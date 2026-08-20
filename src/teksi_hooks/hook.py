from __future__ import annotations

import abc
import dataclasses
import importlib.util
import inspect
import logging
import sys
import time
import uuid
from pathlib import Path
from typing import Any, TypeVar
from types import ModuleType

from .exceptions import TeksiHookError


T = TypeVar("T")
logger = logging.getLogger(__name__)


@dataclasses.dataclass(slots=True, frozen=True)
class HookMetadata:
    """
    Describes a hook implementation.

    Metadata is used for validation, logging and user-facing diagnostics.
    """

    name: str = dataclasses.field(
        metadata={"doc": ("Human-readable hook name used in logs and diagnostics.")},
    )

    description: str = dataclasses.field(
        metadata={"doc": ("Short description of what the hook does.")},
    )


@dataclasses.dataclass(slots=True)
class HookContext:
    """
    Runtime context passed to hook implementations.

    The context contains user/configuration parameters, a logger and the
    capabilities available to the current hook run.
    """

    parameters: dict[str, Any] = dataclasses.field(
        default_factory=dict,
        metadata={
            "doc": (
                "Runtime parameters passed to the hook. These may come from "
                "configuration, command-line options or the calling workflow."
            )
        },
    )

    logger: logging.Logger = dataclasses.field(
        default_factory=lambda: logging.getLogger(__name__),
        metadata={
            "doc": ("Logger that hook implementations should use for runtime messages.")
        },
    )

    capabilities: dict[type[Any], Any] = dataclasses.field(
        default_factory=dict,
        metadata={
            "doc": (
                "Available capabilities keyed by their capability type. Hooks "
                "declare required capability types via `required_capabilities` "
                "and retrieve them with `capability(...)`."
            )
        },
    )

    def capability(
        self,
        capability_type: type[T],
    ) -> T:
        """
        Return a capability instance by type.

        Raises KeyError if the capability was not provided by the caller.
        """

        return self.capabilities[capability_type]


class HookBase(abc.ABC):
    """
    Base class for executable TEKSI hooks.

    Hook implementations must inherit from this class, provide metadata and
    implement `run_hook`.
    """

    required_capabilities: frozenset[type[Any]] = frozenset()

    @abc.abstractmethod
    def run_hook(
        self,
        context: HookContext,
    ) -> None:
        """
        Execute the hook.

        Hooks may use the supplied context to access parameters, logging and
        capabilities.
        """

        raise NotImplementedError(
            "The run_hook method must be implemented in the subclass."
        )

    @property
    @abc.abstractmethod
    def metadata(
        self,
    ) -> HookMetadata:
        """
        Return hook metadata.
        """

        raise NotImplementedError("HookMetadata must be implemented in the subclass.")


class HookHandler:
    """
    Load, validate and execute a hook file.

    A hook file must define a class named ``Hook`` that inherits from
    ``HookBase``. The handler loads the hook as an isolated Python module,
    validates its metadata and required capabilities, runs it with a supplied
    ``HookContext``, then unloads temporary module and path state.
    """

    def __init__(
        self,
        *,
        file: str | Path,
        base_path: Path | None = None,
    ) -> None:
        """
        Create a hook handler.

        Parameters
        ----------
        file:
            Hook file path. Relative paths are resolved against ``base_path``.
        base_path:
            Optional base directory used to resolve and constrain relative hook
            paths.
        """

        self.base_path = base_path

        self.file = Path(file)
        if not self.file.is_absolute():
            if base_path is None:
                raise ValueError("Base path must be provided for relative hook paths.")

            self.file = (base_path / self.file).resolve()

        self._module: ModuleType | None = None
        self._module_name: str | None = None
        self._hook_class: type[HookBase] | None = None
        self._hook_instance: HookBase | None = None
        self._sys_path_additions: list[str] = []

    @property
    def hook(
        self,
    ) -> HookBase:
        """
        Return the loaded hook instance.

        Raises
        ------
        TeksiHookError
          If the hook has not been loaded.
        """

        if self._hook_instance is None:
            raise TeksiHookError.from_message("Hook has not been loaded.")

        return self._hook_instance

    def validate(
        self,
    ) -> None:
        """
        Load and validate the hook with*ut executing it.
        """

        try:
            self._load()
        finally:
            self._unload()

    def run(
        self,
        context: HookContext,
    ) -> None:
        """
        Load, validate and execute the hook.
        """

        try:
            self._load()

            self._validate_context(
                context,
            )

            started = time.monotonic()

            try:
                logger.info(
                    "Executing hook '%s'.",
                    self.hook.metadata.name,
                )

                try:
                    self.hook.run_hook(
                        context,
                    )
                except Exception as exc:
                    raise TeksiHookError.from_message(
                        f"Execution of hook '{self.file}' failed."
                    ) from exc

            finally:
                duration = time.monotonic() - started

                logger.info(
                    "Hook '%s' finished in %.3f s.",
                    self.hook.metadata.name,
                    duration,
                )

        finally:
            self._unload()

    def _load(
        self,
    ) -> None:
        """
        Load and validate the hook module.
        """

        self._validate_file()

        parent_dir = str(
            self.file.parent.resolve(),
        )

        self._sys_path_additions.append(
            parent_dir,
        )

        if self.base_path is not None:
            base_path_str = str(
                self.base_path.resolve(),
            )

            if base_path_str != parent_dir:
                self._sys_path_additions.append(
                    base_path_str,
                )

        for path in reversed(
            self._sys_path_additions,
        ):
            sys.path.insert(
                0,
                path,
            )

        importlib.invalidate_caches()

        try:
            module_name = f"teksi_hook_{self.file.stem}_{uuid.uuid4().hex}"

            spec = importlib.util.spec_from_file_location(
                module_name,
                self.file,
                submodule_search_locations=[
                    parent_dir,
                ],
            )

            if spec is None or spec.loader is None:
                raise TeksiHookError.from_message(
                    f"Unable to create module specification for '{self.file}'."
                )

            module = importlib.util.module_from_spec(
                spec,
            )

            module.__path__ = [
                parent_dir,
            ]

            sys.modules[module_name] = module

            spec.loader.exec_module(
                module,
            )

            hook_class = getattr(
                module,
                "Hook",
                None,
            )

            if hook_class is None or not inspect.isclass(
                hook_class,
            ):
                raise TeksiHookError.from_message(
                    f"Hook file '{self.file}' must define a class named 'Hook'."
                )

            if not issubclass(
                hook_class,
                HookBase,
            ):
                raise TeksiHookError.from_message(
                    f"Class 'Hook' in '{self.file}' must inherit from HookBase."
                )

            self._validate_run_hook_signature(
                hook_class,
            )

            self._hook_class = hook_class
            self._hook_instance = hook_class()

            self._validate_metadata()
            self._validate_required_capabilities()

            self._module = module
            self._module_name = module_name

        except Exception:
            self._cleanup_sys_path()

            if self._module_name is not None:
                sys.modules.pop(
                    self._module_name,
                    None,
                )

            raise

    def _unload(
        self,
    ) -> None:
        """
        Unload hook resources and temporary import state.
        """

        self._cleanup_sys_path()

        if self._module_name is not None:
            sys.modules.pop(
                self._module_name,
                None,
            )

        self._module = None
        self._module_name = None
        self._hook_class = None
        self._hook_instance = None

    def _validate_file(
        self,
    ) -> None:
        """
        Validate the hook file path.
        """

        if not self.file.exists():
            raise TeksiHookError.from_message(
                f"Hook file '{self.file}' does not exist."
            )

        if not self.file.is_file():
            raise TeksiHookError.from_message(f"Hook file '{self.file}' is not a file.")

        if self.file.suffix.lower() != ".py":
            raise TeksiHookError.from_message(
                f"Unsupported hook file type '{self.file.suffix}'."
            )

        if self.base_path is not None:
            try:
                self.file.relative_to(
                    self.base_path.resolve(),
                )
            except ValueError as exc:
                raise TeksiHookError.from_message(
                    f"Hook file '{self.file}' is outside base path '{self.base_path}'."
                ) from exc

    def _validate_context(
        self,
        context: HookContext,
    ) -> None:
        """
        Validate that all required capabilities are available.
        """

        for capability_type in self.hook.required_capabilities:
            if capability_type not in context.capabilities:
                raise TeksiHookError.from_message(
                    f"Required capability '{capability_type.__name__}' is missing."
                )

    def _cleanup_sys_path(
        self,
    ) -> None:
        """
        Remove temporary sys.path additions.
        """

        for path in self._sys_path_additions:
            try:
                sys.path.remove(
                    path,
                )
            except ValueError:
                pass

        self._sys_path_additions.clear()

    def _validate_run_hook_signature(
        self,
        hook_class: type[HookBase],
    ) -> None:
        """
        Validate that Hook.run_hook has the expected signature.
        """

        signature = inspect.signature(
            hook_class.run_hook,
        )

        parameters = list(
            signature.parameters.values(),
        )

        if len(parameters) != 2:
            raise TeksiHookError.from_message("run_hook(self, context) expected.")

        if parameters[0].name != "self":
            raise TeksiHookError.from_message("run_hook(self, context) expected.")

        if parameters[1].name != "context":
            raise TeksiHookError.from_message("run_hook(self, context) expected.")

    def _validate_metadata(
        self,
    ) -> None:
        """
        Validate hook metadata.
        """

        metadata = self.hook.metadata

        if not isinstance(
            metadata,
            HookMetadata,
        ):
            raise TeksiHookError.from_message(
                "metadata must return a HookMetadata instance."
            )

        if not metadata.name.strip():
            raise TeksiHookError.from_message("Hook metadata name must not be empty.")

        if not metadata.description.strip():
            raise TeksiHookError.from_message(
                "Hook metadata description must not be empty."
            )

    def _validate_required_capabilities(
        self,
    ) -> None:
        """
        Validate the hook's required capability declaration.
        """

        capabilities = self.hook.required_capabilities

        if not isinstance(
            capabilities,
            frozenset,
        ):
            raise TeksiHookError.from_message(
                "required_capabilities must be a frozenset."
            )

        for capability in capabilities:
            if not isinstance(
                capability,
                type,
            ):
                raise TeksiHookError.from_message(
                    "required_capabilities must contain capability types."
                )
