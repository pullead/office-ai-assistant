# -*- coding: utf-8 -*-
import unittest
from src.core.email_sender import EmailSender

class TestEmail(unittest.TestCase):
    def test_constructor(self):
        sender = EmailSender("smtp.example.com", 587, "test@example.com", "pass")
        self.assertEqual(sender.smtp_server, "smtp.example.com")

if __name__ == '__main__':
    unittest.main()