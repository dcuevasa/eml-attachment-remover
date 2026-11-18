import tempfile
import unittest
from email import policy
from email.parser import BytesParser
from pathlib import Path

from strip_eml_attachments import remove_attachments, strip_eml


class StripEmlAttachmentsTest(unittest.TestCase):
    def test_removes_attachment_and_preserves_inline_image(self):
        from email.mime.application import MIMEApplication
        from email.mime.image import MIMEImage
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        message = MIMEMultipart()
        message["Subject"] = "Test"
        message.attach(MIMEText("Hello"))

        inline = MIMEImage(b"inline-data", _subtype="png")
        inline.add_header("Content-Disposition", "inline", filename="logo.png")
        message.attach(inline)

        attachment = MIMEApplication(b"attachment-data", "pdf")
        attachment.add_header(
            "Content-Disposition", "attachment", filename="report.pdf"
        )
        message.attach(attachment)

        removed = remove_attachments(message)
        dispositions = [
            part.get_content_disposition()
            for part in message.walk()
            if not part.is_multipart()
        ]

        self.assertEqual(removed, 1)
        self.assertIn("inline", dispositions)
        self.assertNotIn("attachment", dispositions)

    def test_strips_file_and_writes_output(self):
        from email.mime.application import MIMEApplication
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        message = MIMEMultipart()
        message["Subject"] = "Test"
        message.attach(MIMEText("Hello"))
        attachment = MIMEApplication(b"data")
        attachment.add_header(
            "Content-Disposition", "attachment", filename="file.bin"
        )
        message.attach(attachment)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "source.eml"
            destination = temp / "result.eml"
            source.write_bytes(message.as_bytes())

            removed = strip_eml(source, destination)
            parsed = BytesParser(policy=policy.default).parsebytes(
                destination.read_bytes()
            )

            self.assertEqual(removed, 1)
            self.assertFalse(
                any(
                    part.get_content_disposition() == "attachment"
                    for part in parsed.walk()
                )
            )


if __name__ == "__main__":
    unittest.main()
