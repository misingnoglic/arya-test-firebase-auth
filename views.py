import datetime
import os
import uuid

import firebase_admin
import firebase_admin.firestore
import flask
from flask_dance.contrib.google import make_google_blueprint, google
import flask_login

from project_secrets import secrets


# Flags needed to run oauth locally
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

app = flask.Flask(__name__)
app.secret_key = secrets.secret_key
app.debug = True

blueprint = make_google_blueprint(
    client_id=secrets.GOOGLE_CLIENT_ID,
    client_secret=secrets.GOOGLE_CLIENT_SECRET,
    redirect_to='redirect_after_login',
    scope=["profile", "email"]
)
app.register_blueprint(blueprint, url_prefix="/login")

login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_user'

cred = firebase_admin.credentials.Certificate(
    "project_secrets/firebase_key.json")
firebase_admin.initialize_app(cred)
firebase_client = firebase_admin.firestore.client()


class AppUser(object):
    def __init__(self, oauth_response):
        self.user_id = oauth_response.get('sub')
        self.email = oauth_response.get('email')
        self.first_name = oauth_response.get('given_name')
        self.last_name = oauth_response.get('family_name')
        self.full_data = oauth_response

    def get_id(self):
        return self.user_id

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False


@login_manager.user_loader
def load_user(user_id):
    username_collection = firebase_client.collection('Users')
    user = username_collection.document(user_id).get()
    if not user.exists:
        data = google.get("/oauth2/v3/userinfo").json()
        username_collection.document(user_id).set(data)
        user = username_collection.document(user_id).get()
    data = user.to_dict()
    return AppUser(data)

@app.route("/login")
def login_user():
    if not google.authorized:
        return flask.redirect(flask.url_for("google.login"))
    return flask.redirect(flask.url_for('redirect_after_login'))

@app.route("/app_login")
def redirect_after_login():
    data = google.get("/oauth2/v3/userinfo").json()
    flask_login.login_user(AppUser(data))
    return flask.redirect(flask.url_for('index'))

@app.route("/")
@flask_login.login_required
def index():
    return flask.jsonify({
        'urEmail': flask_login.current_user.email
    })

@app.route("/get-thoughts")
@flask_login.login_required
def get_thoughts():
    thought_collection = firebase_client.collection('Thoughts')
    return flask.jsonify({
        'thoughts': [
            thought.to_dict() for thought in thought_collection.order_by(
                'TimeAdded', direction='DESCENDING'
            ).where(
                'UserId', '==', flask_login.current_user.get_id()
            ).stream()
        ]
    })

@app.route("/add-thought", methods=['POST'])
@flask_login.login_required
def add_thought():
    thought_collection = firebase_client.collection('Thoughts')
    new_thought = flask.request.get_json().get('thought')
    thought_collection.document(str(uuid.uuid4())).set({
        'UserId': flask_login.current_user.get_id(),
        'Thought': new_thought,
        'TimeAdded': datetime.datetime.now()
    })
    return flask.jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
