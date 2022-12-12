"""Message model tests."""

# run these tests like:
#
#    python -m unittest test_message_model.py


import os
from unittest import TestCase

from models import db, User, Message, Likes
from sqlalchemy import exc


os.environ['DATABASE_URL'] = "postgresql:///warbler-test"



from app import app



db.create_all()

class MessageModelTestCase(TestCase):
    """Test model for messages."""

    def setUp(self):
        db.drop_all()
        db.create_all()

        self.uid = 989898
        u = User.signup("test5", "test5@email.com", "password", None)
        u.id = self.uid
        db.session.commit()

        self.u = User.query.get(self.uid)

        self.client = app.test_client()

    def tearDown(self):
        res = super().setUp()
        db.session.rollback()
        return res
    
    def test_message_model(self):
        """Does basic model work?"""

        m = Message(text="a warble", user_id=self.uid)

        db.session.add(m)
        db.session.commit()

        self.assertEqual(len(self.u.messages), 1)
        self.assertEqual(self.u.messages[0].text, "a warble")

    def test_message_likes(self):
        m1 = Message(text="a warble", user_id=self.uid)

        m2 = Message(text="another warble", user_id=self.uid)

        u = User.signup("test6", "test6@email.com", "password", None)
        uid = 7777
        u.id = uid
        db.session.add_all([m1, m2, u])
        db.session.commit()

        u.likes.append(m1)

        db.session.commit()

        l = Likes.query.filter(Likes.user_id == uid).all()
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0].message_id, m1.id)