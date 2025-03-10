import google.oauth2.id_token
import local_constants
import datetime
import random
from datetime import time
from datetime import date
from flask import Flask, render_template, redirect, request, Response
from google.auth.transport import requests
from google.cloud import datastore, storage



app = Flask(__name__)
datastore_client = datastore.Client()
firebase_request_adapter = requests.Request()


def Query(in_kind):
    query = datastore_client.query(kind=in_kind)
    result = query.fetch()
    if result == None:
        return []
    return list(result)


def next_value(my_value):
    new_value = my_value[:-1]
    new_value += chr(ord(my_value[-1]) + 1)
    return new_value


def NameQuery(in_kind, attr_name, attr_value):
    query = datastore_client.query(kind=in_kind)
    query.add_filter(attr_name, '=', attr_value)
    result = query.fetch()
    if result == None:
        return []
    return list(result)


def NameQuery2(in_kind, attr_name, attr_value):
    query = datastore_client.query(kind=in_kind)
    if attr_value != "":
        query.add_filter(attr_name, '>=', attr_value)
        query.add_filter(attr_name, '<=', next_value(attr_value))
    result = query.fetch()
    if result == None:
        return []
    return list(result)


def create_set(var):
    ids = set()
    for elem in var:
        ids.add(elem['id'])
    return ids
    

def get_next_id(id):
    return id + 1


def find_max(in_set):
    new_in_set = []
    for elem in in_set:
        num = int(elem)
        new_in_set.append(num)
    return max(new_in_set)
    


def get_id():
    post_set = create_set(Query('Post'))
    comments_set = create_set(Query('Comment'))
    photo_set = create_set(Query('Photo'))
    ids = post_set | comments_set | photo_set
    if len(ids) == 0:
        return str(10**63)
    return str(get_next_id(find_max(ids)))


def count(text):
    return len(text) < 200
    

def get_time():
    now = datetime.datetime.now()
    formatted_time = now.strftime("%Y-%m-%d %H:%M:%S.%f")
    return formatted_time

def toTime(in_string):
    return datetime.datetime.strptime(in_string, "%Y-%m-%d %H:%M:%S.%f")

    
def retrieveUserId(claims):
    id = claims['email']
    return id


def retrieveEntityById(kind, id):
    key = datastore_client.key(kind, id)
    return datastore_client.get(key)


def retrieveUser(claims):
    id = retrieveUserId(claims)
    key = datastore_client.key('User', id)
    user = datastore_client.get(key)
    return id, user


def createUser(claims, user_name, profile_name):
    prev_users = NameQuery('User', 'user_name', user_name)
    if prev_users:
        return -1
    id = claims['email']
    user_key = datastore_client.key('User', id)
    user = datastore.Entity(key = user_key)
    user.update({
        'id' : id,
        'user_name' : user_name,
        'profile_name' : profile_name,
        'followers' : [],
        'followings' : [],
        'posts' : []
    })
    datastore_client.put(user)
    return id


def Follow(user_id, cur_id):
    user = retrieveEntityById('User', user_id)
    cur_user = retrieveEntityById('User', cur_id)
    user_followers = user['followers']
    if cur_id not in user_followers:
        user_followers.append(cur_id)
    user.update({
        'followers' : user_followers
    })
    datastore_client.put(user)
    cur_user_following = cur_user['followings']
    if user_id not in cur_user_following:
        cur_user_following.append(user_id)
    cur_user.update({
        'followings' : cur_user_following
    })
    datastore_client.put(cur_user)


def Unfollow(user_id, cur_id):
    user = retrieveEntityById('User', user_id)
    cur_user = retrieveEntityById('User', cur_id)
    user_followers = user['followers']
    if cur_id in user_followers:
        user_followers.remove(cur_id)
    user.update({
        'followers' : user_followers
    })
    datastore_client.put(user)
    cur_user_following = cur_user['followings']
    if user_id in cur_user_following:
        cur_user_following.remove(user_id)
    cur_user.update({
        'followings' : cur_user_following
    })
    datastore_client.put(cur_user)



def CreateComment(post_id, user_id, comment_text):
    post = retrieveEntityById("Post", post_id)
    id = get_id()
    comment_key = datastore_client.key('Comment', id)
    comment = datastore.Entity(key = comment_key)
    comment.update({
        'id' : id,
        'text' : comment_text,
        'user_id' : user_id
    })
    datastore_client.put(comment)
    post_comments = post['comments']
    post_comments.append(id)
    post.update({
        'comments' : post_comments
    })
    datastore_client.put(post)



def addFile(file):
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
    blob = bucket.blob(file.filename)
    blob.upload_from_file(file, predefined_acl="publicRead")
    public_url = blob.public_url
    return public_url


def createPost(user_id, public_url, caption):
    id = get_id()
    post_key = datastore_client.key('Post', id)
    post = datastore.Entity(key = post_key)
    post.update({
        'id' : id,
        'picture' : public_url,
        'caption' : caption,
        'user_id' : user_id,
        'time' : get_time(),
        'comments' : []
    })
    datastore_client.put(post)
    user = retrieveEntityById('User', user_id)
    user_posts = user['posts']
    user_posts.append(id)
    user.update({
        'posts' : user_posts
    })
    datastore_client.put(user)
    

def the_sorting(inds, A):
    return [A[inds[i]] for i in range(len(inds))]


@app.route('/followers/<string:user_id>')
def followers(user_id):
    id_token = request.cookies.get("token")
    error_message = None
    accept = True
    followers = None
    your_page = False
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            user = retrieveEntityById('User', user_id)
            user_name = user['user_name']
            cur_id = retrieveUserId(claims)
            if user_id == cur_id:
                your_page = True
            followers_ids = user['followers'][::-1]
            followers = [retrieveEntityById('User', followers_ids)['user_name']
                          for followers_ids in followers_ids]
        except ValueError as exc:
            accept = False
            error_message = str(exc)
    return render_template('followers.html', error_message=error_message, user_id=user_id, cur_id=cur_id, user_name=user_name,
                           accept=accept, followers=followers, followers_ids=followers_ids, your_page = your_page)


@app.route('/create_post/<string:user_id>/<path:public_url>', methods=['POST'])
def CreatePost(user_id, public_url):
    id_token = request.cookies.get("token")
    error_message = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            caption = request.form["caption"]
            if len(caption) == 0:
                return render_template('add_caption.html', error="You forgot to add a caption", error_message=error_message, 
                           accept=True, cur_id=user_id, public_url=public_url)
            createPost(user_id, public_url, caption)
        except ValueError as exc:
            pass
    return redirect('/profile_page/' + user_id)



@app.route('/upload_file/<string:user_id>', methods=['post'])
def UploadFile(user_id):
    id_token = request.cookies.get("token")
    claims = None
    cur_id = None
    error_message = None
    accept = True
    public_url = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            cur_id = retrieveUserId(claims)
            file = request.files['file_name']
            filename = file.filename
            if len(filename) < 4:
                error_message = 'The fileformat is wrong'
            if filename[- 4:] not in {'.png', '.jpg'}:
                error_message = 'The fileformat is wrong'
            else:
                public_url = addFile(file)
        except ValueError as exc:
            error_message = str(exc)
            accept = False
    return render_template('add_caption.html', error_message=error_message, 
                           accept=accept, cur_id=cur_id, public_url=public_url)


@app.route('/followings/<string:user_id>')
def followings(user_id):
    id_token = request.cookies.get("token")
    error_message = None
    accept = True
    followings = None
    your_page = False
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            user = retrieveEntityById('User', user_id)
            user_name = user['user_name']
            cur_id = retrieveUserId(claims)
            if user_id == cur_id:
                your_page = True
            followings_ids = user['followings'][::-1]
            followings = [retrieveEntityById('User', following_id)['user_name']
                          for following_id in followings_ids]
        except ValueError as exc:
            accept = False
            error_message = str(exc)
    return render_template('followings.html', error_message=error_message, user_id=user_id, cur_id=cur_id, user_name=user_name,
                           accept=accept, followings=followings, followings_ids=followings_ids, your_page=your_page)



@app.route('/search', methods=['GET', 'POST'])
def search():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    accept = True
    user_names = []
    profile_names = []
    user_ids = []
    if request.method == 'POST':
        profile_name = request.form['profile_name']
        users = NameQuery2('User', 'profile_name', profile_name)
        user_names = [user['user_name'] for user in users]
        profile_names = [user['profile_name'] for user in users]
        user_ids = [user['id'] for user in users]
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            cur_id = retrieveUserId(claims)
        except ValueError as exc:
            accept = False
            error_message = str(exc)
    return render_template('search.html', error_message=error_message, accept=accept, cur_id=cur_id,
                           user_names=user_names, profile_names=profile_names, user_ids=user_ids)





@app.route('/home_page/<string:user_id>')
def HomePage(user_id):
    id_token = request.cookies.get("token")
    error_message = None
    post_ids = None
    posts = None
    post_photos = None
    post_captions = None
    post_user_ids = None
    post_users = None
    post_user_names = None
    post_profile_names = None
    comment_users = None
    comment_texts = None
    cur_id = user_id
    accept = True
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            user = retrieveEntityById('User', user_id)
            post_ids = user['posts']
            user_followings = user['followings']
            for following in user_followings:
                user_following = retrieveEntityById('User', following)
                following_posts = user_following['posts']
                post_ids.extend(following_posts)
            posts = [retrieveEntityById('Post', post_id) for post_id in post_ids]
            post_photos = [post['picture'] for post in posts]
            post_times = [toTime(post['time']) for post in posts]
            post_captions = [post['caption'] for post in posts]
            post_user_ids = [post['user_id'] for post in posts]
            post_users = [retrieveEntityById('User', post_user_id) for post_user_id in post_user_ids]
            post_user_names = [post_user['user_name'] for post_user in post_users]
            post_profile_names = [post_user['profile_name'] for post_user in post_users]
            inds = sorted(range(len(post_times)), key=lambda i: post_times[i], reverse=True)
            post_ids = the_sorting(inds, post_ids)[:50]
            post_photos = the_sorting(inds, post_photos)[:50]
            post_captions = the_sorting(inds, post_captions)[:50]
            post_user_ids = the_sorting(inds, post_user_ids)[:50]
            post_user_names = the_sorting(inds, post_user_names)[:50]
            post_profile_names = the_sorting(inds, post_profile_names)[:50]
            posts = [retrieveEntityById('Post', post_id) for post_id in post_ids]
            comment_ids = [post["comments"][::-1] for post in posts]
            comments = [[retrieveEntityById('Comment', comment_id) for comment_id in comment_ids[i]] for i in range(len(comment_ids))]
            comment_users = [[retrieveEntityById('User', comment['user_id'])['user_name'] for comment in comments[i]] for i in range(len(comments))]
            comment_texts = [[comment['text'] for comment in comments[i]] for i in range(len(comments))]
        except ValueError as exc:
            accept = False
            error_message = str(exc)
    return render_template('home_page.html', error_message=error_message, accept=accept, user_id=user_id, cur_id=cur_id,
                           post_ids=post_ids, post_photos=post_photos, post_captions=post_captions, post_user_ids=post_user_ids,
                           post_user_names=post_user_names, post_profile_names=post_profile_names, comment_users=comment_users,
                           comment_texts=comment_texts)


@app.route('/add_comment/<string:post_id>/<string:user_id>/<string:page>', methods=['POST'])
def AddComment(post_id, user_id, page):
    id_token = request.cookies.get("token")
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            comment_text = request.form["comment"]
            if count(comment_text):
                CreateComment(post_id, user_id, comment_text)
        except ValueError as exc:
            pass
    if page == "home":
        return redirect('/home_page/' + user_id)
    else:
        return redirect('/see_post/' + post_id)
            




@app.route('/see_post/<string:post_id>')
def Post(post_id):
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    accept = True
    post_photo = None
    post_caption = None
    user_name = None
    comment_users = None
    comment_texts = None
    profile_name = None
    user_id = None
    cur_id = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            post = retrieveEntityById('Post', post_id)
            post_photo = post['picture']
            post_caption = post['caption']
            user_id = post['user_id']
            user = retrieveEntityById('User', user_id)
            user_name = user['user_name']
            profile_name = user['profile_name']
            cur_id = retrieveUserId(claims)
            comment_ids = post["comments"][::-1]
            comments = [retrieveEntityById('Comment', comment_id) for comment_id in comment_ids]
            comment_users = [retrieveEntityById('User', comment['user_id'])['user_name'] for comment in comments]
            comment_texts = [comment['text'] for comment in comments]
        except ValueError as exc:
            accept = False
            error_message = str(exc)
    return render_template('post.html', error_message=error_message, accept=accept, user_id=user_id, cur_id=cur_id,
                           post_photo=post_photo, post_caption=post_caption, user_name=user_name, profile_name=profile_name,
                           comment_users=comment_users, comment_texts=comment_texts, post_id=post_id)



@app.route('/profile_page/<string:user_id>')
def profilePage(user_id):
    id_token = request.cookies.get("token")
    error_message = None
    user_name = None
    profile_name = None
    num_followers = None
    num_following = None
    claims = None
    accept = True
    your_page = False
    followed = None
    cur_id = None
    posts = None
    post_pictures = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            user = retrieveEntityById('User', user_id)
            user_name = user['user_name']
            profile_name = user['profile_name']
            num_followers = len(user['followers'])
            num_following = len(user['followings'])
            cur_id = retrieveUserId(claims)
            if user_id == cur_id:
                your_page = True
            else:
                if cur_id in user['followers']:
                    followed = True
                else:
                    followed = False
            posts = user['posts'][::-1]
            post_pictures = [retrieveEntityById('Post', post_id)['picture'] for post_id in posts]
        except ValueError as exc:
            accept = False
            error_message = str(exc)
    return render_template('profile.html', error_message=error_message, accept=accept, posts=posts, post_urls=post_pictures,
                           user_name=user_name, user_id=user_id, cur_id=cur_id, profile_name=profile_name, num_followers=num_followers, 
                           num_following=num_following, your_page=your_page, followed=followed)


@app.route('/create_profile', methods=['GET', 'POST'])
def createProfile():
    id_token = request.cookies.get("token")
    error_message = None
    accept = True
    created = False
    failed = False
    id = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            if request.method == 'POST':
                user_name = request.form['user_name']
                profile_name = request.form['profile_name']
                id = createUser(claims, user_name, profile_name)
                if id != -1:
                    created = True
                else:
                    failed = True
        except ValueError as exc:
            accept = False
            error_message = str(exc)
    return render_template('create_profile.html', error_message=error_message, accept=accept, created=created, failed=failed,
                           id=id)



@app.route('/follow/<string:user_id>')
def follow(user_id):
    id_token = request.cookies.get("token")
    claims = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            cur_id = retrieveUserId(claims)
            Follow(user_id, cur_id)
        except ValueError as exc:
            pass
    return redirect('/profile_page/' + user_id)



@app.route('/unfollow/<string:user_id>')
def unfollow(user_id):
    id_token = request.cookies.get("token")
    claims = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            cur_id = retrieveUserId(claims)
            Unfollow(user_id, cur_id)
        except ValueError as exc:
            pass
    return redirect('/profile_page/' + user_id)



@app.route('/')
def root():
    id_token = request.cookies.get("token")
    error_message = None
    accept = True
    id = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            id, user = retrieveUser(claims)
            if user == None:
                return redirect('/create_profile')
        except ValueError as exc:
            accept = False
            error_message = str(exc)
    if id is None:
        return render_template('profile.html', accept=False, error_message="token expired")
    return redirect('/profile_page/' + id)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)