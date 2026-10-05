import smtplib
from email.message import EmailMessage
from typing import Protocol

from ..exceptions import TeksiHookError
from ..models.mail import Mail, SmtpConfiguration


class MailCapability(Protocol):
    """
    Capability for sending email messages.
    """

    def send(
        self,
        mail: Mail,
    ) -> None: ...


class SmtpMailCapability(
    MailCapability,
):
    """
    SMTP-based implementation of MailCapability.
    """

    def __init__(
        self,
        configuration: SmtpConfiguration,
    ) -> None:
        self._configuration = configuration

    def send(
        self,
        mail: Mail,
    ) -> None:
        message = EmailMessage()

        message["From"] = self._configuration.sender
        message["To"] = ", ".join(
            mail.recipients,
        )

        if mail.cc:
            message["Cc"] = ", ".join(
                mail.cc,
            )

        if mail.bcc:
            message["Bcc"] = ", ".join(
                mail.bcc,
            )

        message["Subject"] = mail.subject
        message.set_content(
            mail.body,
        )

        recipients = list(mail.recipients) + list(mail.cc) + list(mail.bcc)

        try:
            with smtplib.SMTP(
                self._configuration.host,
                self._configuration.port,
            ) as smtp:
                if self._configuration.use_tls:
                    smtp.starttls()

                if self._configuration.username:
                    smtp.login(
                        self._configuration.username,
                        self._configuration.password or "",
                    )

                smtp.send_message(
                    message,
                    to_addrs=recipients,
                )

        except Exception as error:
            raise TeksiHookError.from_message(
                f"Failed to send mail: {error}"
            ) from error
