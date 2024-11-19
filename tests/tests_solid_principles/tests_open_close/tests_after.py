import unittest
from unittest.mock import patch
from faker import Faker
from src.solid_principles.open_close.after import *


class ContactInfoTests(unittest.TestCase):

    def setUp(self):
        self.faker = Faker(locale="es_AR")

    def test_validate_valid_data(self):
        contact_info = ContactInfo(
            email=self.faker.email(),
            phone=self.faker.phone_number(),
        )
        self.assertIsInstance(contact_info, ContactInfo)

    def test_validate_invalid_data(self):
        with self.assertRaises(ValueError):
            contact_info = ContactInfo(
                email=123456
            )


class CustomerDataTests(unittest.TestCase):

    def setUp(self):
        self.faker = Faker(locale="es_AR")

    def test_validate_valid_data(self):
        customer_data = CustomerData(
            name=self.faker.name(),
            contact_info=ContactInfo(
                email=self.faker.email(),
                phone=self.faker.phone_number(),
            )
        )
        self.assertIsInstance(customer_data, CustomerData)

    def test_validate_invalid_data(self):
        with self.assertRaises(ValueError):
            customer_data = CustomerData(
                contact_info=ContactInfo(
                    email=self.faker.email(),
                    phone=self.faker.phone_number(),
                )
            )


class PaymentDataTests(unittest.TestCase):

    def setUp(self):
        self.faker = Faker(locale="es_AR")

    def test_validate_valid_data(self):
        payment_data = PaymentData(
            amount=self.faker.random_number(digits=4),
            source="tok_visa",
        )
        self.assertIsInstance(payment_data, PaymentData)

    def test_validate_invalid_data(self):
        with self.assertRaises(ValueError):
            payment_data = PaymentData(
                amount=self.faker.random_number(digits=4),
            )


class EmailNotifierTests(unittest.TestCase):

    def setUp(self):
        self.faker = Faker(locale="es_AR")

    @patch('src.solid_principles.open_close.after.smtplib.SMTP')
    def test_send_confirmation_success(self, mock_smtp):
        email_notifier = EmailNotifier()
        customer_data = CustomerData(
            name=self.faker.name(),
            contact_info=ContactInfo(
                email=self.faker.email()
            )
        )
        email_notifier.send_confirmation(customer_data=customer_data)
        mock_smtp.assert_called_once()
        mock_smtp.return_value.starttls.assert_called_once()
        mock_smtp.return_value.login.assert_called_once()
        mock_smtp.return_value.sendmail.assert_called_once()
        mock_smtp.return_value.quit.assert_called_once()

    @patch('src.solid_principles.open_close.after.smtplib.SMTP')
    def test_send_confirmation_failure(self, mock_smtp):
        email_notifier = EmailNotifier()
        customer_data = CustomerData(
            name=self.faker.name(),
            contact_info=ContactInfo(
                email=self.faker.email()
            )
        )
        mock_smtp.side_effect = Exception("Email failed")
        email_notifier.send_confirmation(customer_data=customer_data)
        mock_smtp.assert_called_once()
        with self.assertRaises(Exception):
            raise Exception("Email failed")


class SMSNotifierTests(unittest.TestCase):

    def setUp(self):
        self.faker = Faker(locale="es_AR")

    @patch('src.solid_principles.open_close.after.Client')
    def test_send_confirmation_success(self, mock_client):
        sms_notifier = SMSNotifier()
        customer_data = CustomerData(
            name=self.faker.name(),
            contact_info=ContactInfo(
                phone=self.faker.phone_number()
            )
        )
        sms_notifier.send_confirmation(customer_data=customer_data)
        mock_client.assert_called_once()
        mock_client.return_value.messages.create.assert_called_once()

    @patch('src.solid_principles.open_close.after.Client')
    def test_send_confirmation_failure(self, mock_client):
        sms_notifier = SMSNotifier()
        customer_data = CustomerData(
            name=self.faker.name(),
            contact_info=ContactInfo(
                phone=self.faker.phone_number()
            )
        )
        mock_client.return_value.messages.create.side_effect = Exception("SMS failed")
        sms_notifier.send_confirmation(customer_data=customer_data)
        mock_client.assert_called_once()
        mock_client.return_value.messages.create.assert_called_once()
        with self.assertRaises(Exception):
            raise Exception("SMS failed")


class TransactionLoggerTests(unittest.TestCase):

    def setUp(self):
        self.faker = Faker(locale="es_AR")

    def test_log_transaction(self):
        transaction_logger = TransactionLogger()
        customer_data = CustomerData(
            name="John Doe",
            contact_info=ContactInfo(
                email=self.faker.email()
            )
        )
        payment_data = PaymentData(
            amount=1000,
            source="tok_visa",
        )
        charge = {"status": "succeeded"}
        transaction_logger.log(customer_data, payment_data, charge)
        with open("transactions.log", "r") as log_file:
            logs = log_file.read()
            self.assertIn("John Doe paid 1000", logs)
            self.assertIn("Payment status: succeeded", logs)

    def tearDown(self):
        if os.path.exists("transactions.log"):
            os.remove("transactions.log")


class StripePaymentProcessorTests(unittest.TestCase):

    def setUp(self):
        self.faker = Faker(locale="es_AR")

    @patch('src.solid_principles.open_close.after.stripe.Charge.create')
    def test_process_transaction_success(self, mock_charge):
        stripe_payment_processor = StripePaymentProcessor()
        mock_charge.return_value = {"status": "succeeded"}
        customer_data = CustomerData(
            name="John Doe",
            contact_info=ContactInfo(
                email=self.faker.email()
            )
        )
        payment_data = PaymentData(
            amount=1000,
            source="tok_visa",
        )
        charge = stripe_payment_processor.process_transaction(customer_data, payment_data)
        self.assertEqual(charge["status"], "succeeded")

    @patch('src.solid_principles.open_close.after.stripe.Charge.create')
    def test_process_transaction_failure(self, mock_charge):
        stripe_payment_processor = StripePaymentProcessor()
        mock_charge.side_effect = StripeError("Payment failed")
        customer_data = CustomerData(
            name="John Doe",
            contact_info=ContactInfo(
                email=self.faker.email()
            )
        )
        payment_data = PaymentData(
            amount=1000,
            source="tok_visa",
        )
        with self.assertRaises(StripeError):
            stripe_payment_processor.process_transaction(customer_data, payment_data)


class PaymentServiceTests(unittest.TestCase):

    def setUp(self):
        self.faker = Faker(locale="es_AR")

    @patch('src.solid_principles.open_close.after.EmailNotifier.send_confirmation')
    @patch('src.solid_principles.open_close.after.TransactionLogger.log')
    @patch('src.solid_principles.open_close.after.StripePaymentProcessor.process_transaction')
    def test_process_transaction_success(self, mock_process_transaction, mock_log, mock_send_confirmation):
        payment_service = PaymentService()
        mock_process_transaction.return_value = {"status": "succeeded"}
        customer_data = CustomerData(
            name="John Doe",
            contact_info=ContactInfo(
                email=self.faker.email()
            )
        )
        payment_data = PaymentData(
            amount=1000,
            source="tok_visa",
        )
        charge = payment_service.process_transaction(customer_data, payment_data)
        self.assertEqual(charge["status"], "succeeded")
        mock_send_confirmation.assert_called_once()
        mock_log.assert_called_once()

    @patch('src.solid_principles.open_close.after.EmailNotifier.send_confirmation')
    @patch('src.solid_principles.open_close.after.TransactionLogger.log')
    @patch('src.solid_principles.open_close.after.StripePaymentProcessor.process_transaction')
    def test_process_transaction_failure(self, mock_process_transaction, mock_log, mock_send_confirmation):
        payment_service = PaymentService()
        mock_process_transaction.side_effect = StripeError("Payment failed")
        customer_data = CustomerData(
            name="John Doe",
            contact_info=ContactInfo(
                email=self.faker.email()
            )
        )
        payment_data = PaymentData(
            amount=1000,
            source="tok_visa",
        )
        with self.assertRaises(StripeError):
            payment_service.process_transaction(customer_data, payment_data)
        mock_send_confirmation.assert_not_called()
        mock_log.assert_not_called()