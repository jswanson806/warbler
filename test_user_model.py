"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase
from sqlalchemy import exc

from models import db, User, Message, Follows

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class UserModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        user1 = User.signup('user1', 'user1@email.com', 'password', None)
        uid1 = 1111
        user1.id = uid1
        user2 = User.signup('user2', 'user2@email.com', 'password', None)
        uid2 = 2222
        user2.id = uid2
        
        db.session.commit()
        
        u1 = User.query.get(uid1)
        u2 = User.query.get(uid2)

        self.u1 = u1
        self.uid1= uid1

        self.u2 = u2
        self.uid2 = uid2

        self.client = app.test_client()
    
    def tearDown(self):
        res = super().tearDown()
        db.session.rollback()
        return res

    def test_user_model(self):
        """Does basic model work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)

    def test_user_follows(self):
        """Is following tracking the follower and following correctly?"""
        # add user 2 to user 1 following
        self.u1.following.append(self.u2)
        db.session.commit()

        # verify followers and following count updates
        self.assertEqual(len(self.u2.following), 0)
        self.assertEqual(len(self.u2.followers), 1)
        self.assertEqual(len(self.u1.following), 1)
        self.assertEqual(len(self.u1.followers), 0)
        # verify user 1 is following user2 and vice versa
        self.assertEqual(self.u2.followers[0].id, self.u1.id)
        self.assertEqual(self.u1.following[0].id, self.u2.id)

    def test_is_following(self):
        # add user2 to user1 following
        self.u1.following.append(self.u2)
        db.session.commit()

        self.assertTrue(self.u1.is_following(self.u2))
        self.assertFalse(self.u2.is_following(self.u1))

    def test_is_followed_by(self):
        self.u1.following.append(self.u2)
        db.session.commit()

        self.assertTrue(self.u1.is_following(self.u2))
        self.assertFalse(self.u2.is_following(self.u1))

    def test_valid_signup(self):
        u_test = User.signup("testuser2", "testuser2@email.com", "password", None)
        uid = 3333
        u_test.id = uid
        db.session.commit()

        u_test = User.query.get(uid)
        self.assertIsNotNone(u_test)

        self.assertEqual(u_test.username, "testuser2")
        self.assertEqual(u_test.email, "testuser2@email.com")
        self.assertNotEqual(u_test.password, "password")
        self.assertTrue(u_test.password.startswith("$2b$"))
    
    def test_invalid_email_signup(self):
        invalid = User.signup("testuser3", None, "password", None)
        uid = 4444
        invalid.id = uid
        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()

    def test_invalid_username_signup(self):
        invalid = User.signup(None, "testuser3@email.com", "password", None)
        uid = 5555
        invalid.id = uid
        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()
            
    def test_invalid_email_signup(self):
        invalid = User.signup("testuser3", None, "password", None)
        uid = 4444
        invalid.id = uid
        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()

    def test_invalid_passwword_signup(self):
        with self.assertRaises(ValueError) as context:
            User.signup('test', 'test@email.com', "", None)

        with self.assertRaises(ValueError) as context:
            User.signup('test', 'test@email.com', None, None)


    def test_valid_auth(self):
        u = User.authenticate(self.u1.username, "password")
        self.assertIsNotNone(u)
        self.assertEqual(u.id, self.uid1)

    def test_invalid_username(self):
        self.assertFalse(User.authenticate("notthisname", "password"))

    def test_wrong_password(self):
        self.assertFalse(User.authenticate(self.u1.username, "notthisone"))