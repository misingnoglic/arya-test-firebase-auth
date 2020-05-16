import datetime
import uuid

import firebase_admin
import firebase_admin.firestore



def get_password(username, collection):
    results = list(collection.where('Username', '==', username).stream())
    if len(results) == 0:
        raise Exception("No users by that username")
    if len(results) > 1:
        raise Exception("Invalid Data")

    return results[0].to_dict().get("Password")

def create_user(username, password, email, collection):
    collection.document(email).set({
        'Username': username,
        'Password': password,
    })

def make_thought(email, thought, collection):
    collection.document(str(uuid.uuid4())).set({
        'Email': email,
        'Thought': thought,
        'TimeAdded': datetime.datetime.now()-datetime.timedelta(days=365)
    })

def get_thoughts(email, collection):
    return [x.to_dict() for x in collection.order_by(
        'TimeAdded').where(
        'Email', '==', email).stream()]

if __name__ == '__main__':
    cred = firebase_admin.credentials.Certificate(
        "secrets/key.json")
    firebase_admin.initialize_app(cred)
    client = firebase_admin.firestore.client()
    username_collection = client.collection('Users')
    thought_collection = client.collection('Thoughts')
    choice = int(input("Press 1 to get your pw, 2 to make an account, 3 to add a thought, 4 to get your thoughts: "))
    if choice == 1:
        username = input("What's your username: ")
        password = get_password(username, username_collection)
        print(f'Your password is {password}')
    if choice == 2:
        email = input("What's your email: ")
        username = input("Choose a username: ")
        password = input("Choose a password: ")
        create_user(username, password, email, username_collection)
    if choice == 3:
        email = input("What's your email: ")
        thought = input("What's your thought: ")
        make_thought(email, thought, thought_collection)
    if choice == 4:
        email = input("What's your email: ")
        thoughts = get_thoughts(email, thought_collection)
        for thought in thoughts:
            print(thought.get('Thought'))