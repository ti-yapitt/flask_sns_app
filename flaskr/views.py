from datetime import datetime
from flask import Blueprint, abort, request, render_template, redirect, url_for, flash, session, jsonify
from flask_login import login_user, login_required, logout_user
from flaskr.models import User, PasswordResetToken, UserConnect, Message
from flaskr import db
from os import path
from flaskr.forms import LoginForm, RegisterForm, ResetPasswordForm, ForgotPasswordForm, UserForm, ChangePasswordForm, UserSearchForm, ConnectForm, MessageForm
from flask_login import current_user
from flaskr.utils.message_format import make_message_format


bp = Blueprint('app', __name__, url_prefix='')

@bp.route('/')
def home():
    friends = requested_friends = requesting_friends = None
    connect_form = ConnectForm()
    session['url'] = 'app.home'
    if current_user.is_authenticated:
        friends = User.select_friends()
        requested_friends = User.select_requested_friends()
        requesting_friends = User.select_requesting_friends()
    return render_template(
        'home.html',
        friends = friends,
        requested_friends = requested_friends,
        requesting_friends = requesting_friends,
        connect_form=connect_form
    )

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('app.home'))

@bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        user = User.select_user_by_email(form.email.data)
        if user and user.is_active and user.validate_password(form.password.data):
            login_user(user, remember=True)
            next = request.args.get('next')
            if not next:
                next = url_for('app.home')
            return redirect(next)
        elif not user:
            flash('存在しないユーザです')
        elif not user.is_active:
            flash('無効なユーザです。パスワードを再設定してください')
        elif not user.validate_password(form.password.data):
            flash('メールアドレスとパスワードの組み合わせが誤っています')
    return render_template('login.html', form=form)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        user = User(
            username = form.username.data,
            email = form.email.data,
        )
        with db.session.begin(subtransactions=True):
            user.create_new_user()
        db.session.commit()
        token = ''
        with db.session.begin(subtransactions=True):
            token = PasswordResetToken.publish_token(user)
        db.session.commit()
        print(f'パスワード設定用URL: http://127.0.0.1:5000/reset_password/{token}')
        flash('パスワード設定用のURLをお送りしました。ご確認ください')
        return redirect(url_for('app.home'))
    return render_template('register.html', form=form)

@bp.route('/reset_password/<uuid:token>', methods=['POST', 'GET'])
def reset_password(token):
    form = ResetPasswordForm(request.form)
    reset_user_id = PasswordResetToken.get_user_id_by_token(token)
    if not reset_user_id:
        abort(500)
    if request.method == 'POST' and form.validate():
        password = form.password.data
        user = User.select_user_by_id(reset_user_id)
        with db.session.begin(subtransactions=True):
            user.save_new_password(password)
            PasswordResetToken.delete_token(token)
        db.session.commit()
        flash('パスワードを更新しました')
        return redirect(url_for('app.login'))
    return render_template('reset_password.html', form=form)

@bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm(request.form)
    if request.method == 'POST' and form.validate():
        email = form.email.data
        user = User.select_user_by_email(email)
        if user:
            with db.session.begin(subtransactions=True):
                token = PasswordResetToken.publish_token(user)
            db.session.commit()
            reset_url = f'http://127.0.0.1:5000/reset_password/{token}'
            print(reset_url)
            flash('パスワード再登録用のURLを発行しました')
        else:
            flash('そのユーザは存在しません')
    return render_template('forgot_password.html', form=form)

@bp.route('/user', methods=['GET', 'POST'])
@login_required
def user():
    form = UserForm(request.form)
    if request.method == 'POST' and form.validate():
        user_id = current_user.get_id()
        user = User.select_user_by_id(user_id)
        with db.session.begin(subtransactions=True):
            user.username = form.username.data
            user.email = form.email.data
            file = request.files[form.picture_path.name].read()
            if file:
                file_name = user_id + '_' + str(int(datetime.now().timestamp())) + '.jpg'
                picture_path = 'flaskr/static/user_image/' + file_name
                open(picture_path, 'wb').write(file)               #指定した保存先にファイルを保存している#
                user.picture_path = 'user_image/' + file_name
        db.session.commit()
        flash('ユーザ情報が更新されました')
    return render_template('user.html', form=form)

@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm(request.form)
    if request.method == 'POST' and form.validate():
        user = User.select_user_by_id(current_user.get_id())
        password = form.password.data
        with db.session.begin(subtransactions=True):
            user.save_new_password(password)
        db.session.commit()
        flash('パスワードが更新されました')
        return redirect(url_for('app.user'))
    return render_template('change_password.html', form=form)

@bp.route('/user_search', methods=['GET', 'POST'])
@login_required
def user_search():
    form = UserSearchForm(request.form)
    connect_form = ConnectForm()
    session['url'] = 'app.user_search'
    users = None
    if request.method == 'POST' and form.validate():
        username = form.username.data
        users = User.search_by_name(username)
    return render_template('user_search.html', form=form, users=users, connect_form=connect_form)

@bp.route('/connect_user', methods=['POST', 'GET'])
@login_required
def connect_user():
    form = ConnectForm(request.form)
    if request.method == 'POST' and form.validate():
        if form.connect_condition.data == 'connect':
            new_connect = UserConnect(current_user.get_id(), form.to_user_id.data)
            with db.session.begin(subtransactions=True):
                new_connect.create_new_connect()
            db.session.commit()
        elif form.connect_condition.data == 'accept':
            connect = UserConnect.select_by_from_user_id(form.to_user_id.data)
            if connect:
                with db.session.begin(subtransactions=True):
                    connect.update_status()
                db.session.commit()
    next_url = session.pop('url', ('app.home'))
    return redirect(url_for(next_url))

@bp.route('/message/<id>', methods=['GET', 'POST'])
def message(id):
    if not UserConnect.is_friend(id):
        return redirect(url_for('app.home'))
    form = MessageForm(request.form)
    messages = Message.get_friend_messages(current_user.get_id(), id)
    user = User.select_user_by_id(id)
    read_messages_ids = [message.id for message in messages if (not message.is_read) and (message.from_user_id == int(id))]
    if read_messages_ids:
        with db.session.begin(subtransactions=True):
            Message.update_is_read_by_ids(read_messages_ids)
        db.session.commit()
    if request.method == 'POST' and form.validate():
        new_message = Message(current_user.get_id(), id, form.message.data)
        with db.session.begin(subtransactions=True):
            new_message.create_message()
        db.session.commit()
        return redirect(url_for('app.message', id=id))
    return render_template('message.html', form=form, messages=messages, to_user_id=id, user=user)

@bp.route('/message_ajax', methods=['GET', 'POST'])
@login_required
def message_ajax():
    user_id = request.args.get('user_id', -1, type=int)
    user = User.select_user_by_id(user_id)
    not_read_messages = Message.select_not_read_messages(user_id, current_user.get_id())
    not_read_message_ids = [message.id for message in not_read_messages]
    if not_read_message_ids:
        with db.session.begin(subtransactions=True):
            Message.update_is_read_by_ids(not_read_message_ids)
        db.session.commit()
    return jsonify(data=make_message_format(user, not_read_messages))

@bp.app_errorhandler(404)
def page_not_found(e):
    return redirect(url_for('app.home'))

@bp.app_errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500