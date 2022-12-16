from functools import wraps
import sqlalchemy
from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from flask import request
from sqlalchemy.ext.declarative import declarative_base
import os



app = Flask(__name__)
app.config['SECRET_KEY'] = "8BYkEfBA6O6donzWlSihBXox7C0sKR6b"
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("BLOG_APP_DATABASE_URL", "sqlite:///blog.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
Base = declarative_base()

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


##CONFIGURE TABLES
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(), nullable=False)
    name = db.Column(db.String(250), nullable=False)
    blog_posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    author = relationship("User", back_populates="blog_posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship("Comment", back_populates="parent_post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comment_author = relationship("User", back_populates="comments")

    post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'))
    parent_post = relationship("BlogPost", back_populates="comments")
    comment = db.Column(db.Text, nullable=False)


db.create_all()
# post = BlogPost(title="Test Title", author_id=1, subtitle="Test Subtitle", date="10/10/2022", body="Test body", img_url="http://www.google.com/image.png")
# db.session.add(post)
# db.session.commit()


def admin_only(function):
    @wraps(function)
    def wrapper_function(*args, **kwargs):
        if current_user.get_id() == "1":
            return function(*args, **kwargs)
        else:
            return abort(403, "Access Forbidden")
    return wrapper_function


@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except sqlalchemy.exc.InvalidRequestError:
        pass


@app.route('/')
def get_all_posts():
    posts = []
    try:
        posts = BlogPost.query.all()
        return render_template("index.html", all_posts=posts)
    except sqlalchemy.exc.InvalidRequestError:
        return render_template("index.html", all_posts=posts)


@app.route('/register', methods=["GET", "POST"])
def register():
    register_form = RegisterForm()
    if request.method == "GET":
        return render_template("register.html", form=register_form)
    elif request.method == "POST":
        # get user input from form
        user_name = register_form.name.data
        user_email = register_form.email.data
        user_password = register_form.password.data
        hash_password = generate_password_hash(user_password)
        print(user_name)
        print(user_email)
        print(hash_password)

        # add to DB
        new_user = User(
            email=user_email,
            password=hash_password,
            name=user_name
        )
        db.session.add(new_user)
        try:
            db.session.commit()
            user = User.query.filter_by(email=user_email).first()
            login_user(user)
            return redirect(url_for("get_all_posts"))
        except sqlalchemy.exc.IntegrityError:
            flash(message="You've already signed up with that email. Login instead.", category="error")
            return redirect(url_for("login"))


@app.route('/login', methods=["GET", "POST"])
def login():
    login_form = LoginForm()
    if request.method == "GET":
        return render_template("login.html", form=login_form)
    elif request.method == "POST":
        login_user_name = login_form.email.data
        login_password = login_form.password.data
        try:
            find_user = User.query.filter_by(email=login_user_name).one()
            if check_password_hash(find_user.password, login_password):
                login_user(find_user)
                flash(message="You have been successfully logged in.", category="success")
                return redirect(url_for("get_all_posts"))
            else:
                flash("Incorrect login information.", "error")
                return redirect(url_for("login"))
        except sqlalchemy.orm.exc.NoResultFound:
            flash("Incorrect login information.", "error")
            return redirect(url_for("login"))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash(message="You have been successfully logged out.", category="success")
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    post_comments = Comment.query.filter_by(post_id=post_id).all()
    print(f"Comments List: {post_comments}")
    comment_form = CommentForm()
    if request.method == "POST":
        if comment_form.validate_on_submit():
            add_comment = Comment(
                comment=comment_form.comment.data,
                author_id=current_user.id,
                post_id=post_id
            )
            db.session.add(add_comment)
            db.session.commit()
            return redirect(url_for('show_post', post_id=post_id))
    return render_template("post.html", post=requested_post, form=comment_form, comments=post_comments)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if request.method == "POST":
        if form.validate_on_submit():
            new_post = BlogPost(
                title=form.title.data,
                subtitle=form.subtitle.data,
                body=form.body.data,
                img_url=form.img_url.data,
                author=current_user,
                date=date.today().strftime("%B %d, %Y")
            )
            db.session.add(new_post)
            db.session.commit()
            return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["GET","POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if request.method == "POST":
        if edit_form.validate_on_submit():
            post.title = edit_form.title.data
            post.subtitle = edit_form.subtitle.data
            post.img_url = edit_form.img_url.data
            post.author = current_user
            post.body = edit_form.body.data
            db.session.commit()
            return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)
