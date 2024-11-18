import unittest
from unittest.mock import patch
from src.solid_principles.single_responsability.refactoring_code import *


class TestValidatedCustomerData(unittest.TestCase):
    def test_validate_valid_data(self):
        customer_data = {"name": "John Doe", "contact_info": {"email": "john.doe@example.com"}}
        self.assertIsNone(ValidatedCustomerData.validate(customer_data))

    def test_validate_invalid_data(self):
        with self.assertRaises(ValueError):
            ValidatedCustomerData.validate({"contact_info": {"email": "john.doe@example.com"}})


class TestValidatedPaymentData(unittest.TestCase):
    def test_validate_valid_data(self):
        payment_data = {"source": "tok_visa"}
        self.assertIsNone(ValidatedPaymentData.validate(payment_data))

    def test_validate_invalid_data(self):
        with self.assertRaises(ValueError):
            ValidatedPaymentData.validate({"amount": 1000})


class TestNotificationSender(unittest.TestCase):
    @patch('src.solid_principles.single_responsability.refactoring_code.smtplib.SMTP')
    def test_send_email_notification(self, mock_smtp):
        NotificationSender.send_email_notification("test@example.com")
        mock_smtp.assert_called_once()

    @patch('src.solid_principles.single_responsability.refactoring_code.Client')
    def test_send_sms_notification(self, mock_client):
        NotificationSender.send_sms_notification("+1234567890")
        mock_client.assert_called_once()


class TestTransactionLogger(unittest.TestCase):
    def test_log_transaction(self):
        customer_data = {"name": "John Doe"}
        payment_data = {"amount": 1000}
        charge = {"status": "succeeded"}
        TransactionLogger.log_transaction(customer_data, payment_data, charge)
        with open("transactions.log", "r") as log_file:
            logs = log_file.read()
            self.assertIn("John Doe paid 1000 cents", logs)
            self.assertIn("Payment status: succeeded", logs)

    def tearDown(self):
        if os.path.exists("transactions.log"):
            os.remove("transactions.log")


class TestStripePaymentProcessor(unittest.TestCase):
    @patch('src.solid_principles.single_responsability.refactoring_code.stripe.Charge.create')
    def test_process_transaction_success(self, mock_charge):
        mock_charge.return_value = {"status": "succeeded"}
        customer_data = {"name": "John Doe", "contact_info": {"email": "john.doe@example.com"}}
        payment_data = {"amount": 1000, "source": "tok_visa"}
        charge = StripePaymentProcessor.process_transaction(customer_data, payment_data)
        self.assertEqual(charge["status"], "succeeded")

    @patch('src.solid_principles.single_responsability.refactoring_code.stripe.Charge.create')
    def test_process_transaction_failure(self, mock_charge):
        mock_charge.side_effect = StripeError("Payment failed")
        customer_data = {"name": "John Doe", "contact_info": {"email": "john.doe@example.com"}}
        payment_data = {"amount": 1000, "source": "tok_visa"}
        with self.assertRaises(StripeError):
            StripePaymentProcessor.process_transaction(customer_data, payment_data)


if __name__ == "__main__":
    unittest.main()
