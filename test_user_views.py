"""User View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_user_views.py


import os
from unittest import TestCase

from models import db, connect_db, Message, User, Likes, Follows
from bs4 import BeautifulSoup

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


from app import app, CURR_USER_KEY


db.create_all()


app.config['WTF_CSRF_ENABLED'] = False


class UserViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)
        self.user1 = User.signup("user1", "user1@email.com", "password", None)
        self.user2 = User.signup("user2", "user2@email.com", "password", None)
        self.user3 = User.signup("user3", "user3@email.com", "password", None)
        self.user4 = User.signup("user4", "user4@email.com", "password", None)

        db.session.commit()

    def tearDown(self):
        resp = super().tearDown()
        db.session.rollback()
        return resp

    def test_users_create(self):
        """Are users being added to the users table?"""
        with self.client as c:
            resp = c.get('/users')

            self.assertIn("@testuser", str(resp.data))
            self.assertIn("@user1", str(resp.data))
            self.assertIn("@user2", str(resp.data))
            self.assertIn("@user3", str(resp.data))
            self.assertIn("@user4", str(resp.data))

    def test_users_search(self):
        """Does the search return the correct results?"""
        with self.client as c:
            resp = c.get('/users?q=test')

            self.assertIn("@testuser", str(resp.data))

            self.assertNotIn("@user2", str(resp.data))
            self.assertNotIn("@user3", str(resp.data))
            self.assertNotIn("@user4", str(resp.data))

    def test_show_single_user(self):
        """Can we view a single user?"""
        with self.client as c:
            resp = c.get(f'/users/{self.testuser.id}')

            self.assertEqual(resp.status_code, 200)
            self.assertIn("@testuser", str(resp.data))
    
    def setup_likes(self):
        msg1 = Message(text='testing a message', user_id=self.testuser.id)
        msg2 = Message(text='testing a second message', user_id=self.testuser.id)
        msg3 = Message(id=9999, text='testing a third message', user_id=self.user1.id)
        db.session.add_all([msg1, msg2, msg3])
        db.session.commit()

        test_like = Likes(user_id=self.testuser.id, message_id=9999)

        db.session.add(test_like)
        db.session.commit()

    def test_user_show_with_likes(self):
        # setup likes in test db
        self.setup_likes()

        with self.client as c:
            # query a user
            resp = c.get(f"/users/{self.testuser.id}")
            # check status code is 200
            self.assertEqual(resp.status_code, 200)
            # check for the username in the response
            self.assertIn("@testuser", str(resp.data))
            # instantiate instance of BeautifulSoup
            soup = BeautifulSoup(str(resp.data), 'html.parser')
            # find all stat li's in HTML
            found = soup.find_all("li", {"class": "stat"})
            # verify we found 4 results (followers, following, messages, likes)
            self.assertEqual(len(found), 4)
            # verify there are 2 messages
            self.assertIn("2", found[0].text)
            # verify there are 0 followers and following
            self.assertIn("0", found[1].text)
            self.assertIn("0", found[2].text)
            # verify there is 1 like
            self.assertIn("1", found[3].text)

    def test_add_like(self):
        # create a message with specific id
        m = Message(id=99999, text="i am a message", user_id=self.user1.id)
        # add the message to the session
        db.session.add(m)
        # commit
        db.session.commit()
        # fake login
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
        # post request for like on this message
        resp = c.post("/users/add_like/99999", follow_redirects=True)
        # check status code
        self.assertEqual(resp.status_code, 200)

        # query all likes for the message
        likes = Likes.query.filter(Likes.message_id==99999).all()
        # assert the length of likes to be 1
        self.assertEqual(len(likes), 1)
        # assert the like user_id to be self.testuser.id
        self.assertEqual(likes[0].user_id, self.testuser.id)

    def test_remove_like(self):
        """Can we remove a like?"""
        # setup likes in test db
        self.setup_likes()
        # query a message
        m = Message.query.filter(Message.text=='testing a third message').one()
        # make sure the message exists
        self.assertIsNotNone(m)
        # make sure the message.user_id is not the same as testuser.id
        self.assertNotEqual(m.user.id, self.testuser.id)
        
        # query the specific like from message 'i am a message'
        l = Likes.query.filter(Likes.user_id==self.testuser.id and Likes.message_id==m.id).one()

        # Make sure the like we queried is not none
        self.assertIsNotNone(l)

        # set up the client
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
        
        # save post response request
        resp = c.post(f"/users/remove_like/{m.id}", follow_redirects=True)
        # check the response status code
        self.assertEqual(resp.status_code, 200)
        # query all of the m.id likes
        likes = Likes.query.filter(Likes.message_id==m.id).all()
        # check to see if the like was removed by checking the len of likes
        self.assertEqual(len(likes), 0)

    def test_like_unauthorized(self):
        """Can we like a message if we are not logged in?"""
        # setup likes
        self.setup_likes()
        # query a message from another user
        m = Message.query.filter(Message.text=='testing a third message').one()
        self.assertIsNotNone(m)
        # save the current total count of likes
        likes = Likes.query.count()
        # setup client
        with self.client as c:
        # send the post request and save response
            resp = c.post(f'users/add_like/{m.id}', follow_redirects=True)
        # check the status code for 200
            self.assertEqual(resp.status_code, 200)
        # check the response data to include flash message text
            self.assertIn('Access unauthorized', str(resp.data))
        # check that the number of total likes has not changed from earlier
            self.assertEqual(likes, Likes.query.count())

    def setup_followers(self):
        follow1 = Follows(user_being_followed_id=self.user1.id, user_following_id=self.testuser.id)
        follow2 = Follows(user_being_followed_id=self.user2.id, user_following_id=self.testuser.id)
        follow3 = Follows(user_being_followed_id=self.testuser.id, user_following_id=self.user3.id)

        db.session.add_all([follow1, follow2, follow3])
        db.session.commit()

    def test_user_show_with_follows(self):
        # setup followers in test db
        self.setup_followers()

        with self.client as c:
            # query a user
            resp = c.get(f"/users/{self.testuser.id}")
            # check status code is 200
            self.assertEqual(resp.status_code, 200)
            # check for the username in the response
            self.assertIn("@testuser", str(resp.data))
            # instantiate instance of BeautifulSoup
            soup = BeautifulSoup(str(resp.data), 'html.parser')
            # find all stat li's in HTML
            found = soup.find_all("li", {"class": "stat"})
            # verify we found 4 results (followers, following, messages, likes)
            self.assertEqual(len(found), 4)
            # verify there are 0 messages
            self.assertIn("0", found[0].text)
            # verify there are 2 following
            self.assertIn("2", found[1].text)
            # verify there is 1 following
            self.assertIn("1", found[2].text)
            # verify there are 0 likes
            self.assertIn("0", found[3].text)

    def test_show_following(self):
        # setup followers
        self.setup_followers()
        # setup client and session id
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            
            # get following
            resp = c.get(F"/users/{self.testuser.id}/following")
            # check respond code for 200
            self.assertEqual(resp.status_code, 200)
            # check for each follower
            self.assertIn('@user1', str(resp.data))
            self.assertIn('@user2', str(resp.data))
            self.assertNotIn('@user3', str(resp.data))
            self.assertNotIn('@user4', str(resp.data))

    def test_show_followers(self):
        # setup followers
        self.setup_followers()
        # setup client and session id
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            
            # get following
            resp = c.get(F"/users/{self.testuser.id}/followers")
            # check respond code for 200
            self.assertEqual(resp.status_code, 200)
            # check for each follower
            self.assertNotIn('@user1', str(resp.data))
            self.assertNotIn('@user2', str(resp.data))
            self.assertIn('@user3', str(resp.data))
            self.assertNotIn('@user4', str(resp.data))

    def test_following_page_unauthorized(self):
        # setup followers
        self.setup_followers()
        # setup client without login
        with self.client as c:
            # get following
            resp = c.get(F"/users/{self.testuser.id}/following", follow_redirects=True)
            # check respond code for 200
            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('@user3', str(resp.data))
            self.assertIn('Access unauthorized', str(resp.data))

    def test_follower_page_unauthorized(self):
        # setup followers
        self.setup_followers()
        # setup client without login
        with self.client as c:
            # get following
            resp = c.get(F"/users/{self.testuser.id}/followers", follow_redirects=True)
            # check respond code for 200
            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('@user3', str(resp.data))
            self.assertIn('Access unauthorized', str(resp.data))