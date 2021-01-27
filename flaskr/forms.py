from wtforms.form import Form
from wtforms.fields import (
    StringField, FileField, PasswordField, SubmitField, HiddenField, TextAreaField
)
from wtforms.validators import DataRequired, Email, EqualTo
from wtforms import ValidationError
from flaskr.models import User, UserConnect
from flask_login import current_user
from flask import flash


class LoginForm(Form):
    email = StringField('メール: ', validators=[DataRequired(), Email()])
    password = PasswordField('パスワード: ', validators=[DataRequired(), EqualTo('confirm_password', 'パスワードが一致しません')])
    confirm_password = PasswordField('パスワードの確認: ', validators=[DataRequired()])
    submit = SubmitField('ログイン')


class RegisterForm(Form):
    email = StringField('メール: ', validators=[DataRequired(), Email('パスワードが誤っています')])
    username = StringField('ユーザ名: ', validators=[DataRequired()])
    submit = SubmitField('登録')

    def validate_email(self, field):
        if User.select_user_by_email(field.data):
            raise ValidationError('メールアドレスは既に登録されています')


class ResetPasswordForm(Form):
    password = PasswordField(
        'パスワード: ',
        validators=[DataRequired(), EqualTo('confirm_password', message='パスワードが一致しません')]
    )
    confirm_password = PasswordField(
        'パスワード確認: ',
        validators=[DataRequired()]
    )
    submit = SubmitField('パスワードを更新する')

    def validate_password(self, field):
        if len(field.data) < 8:
            raise ValidationError('パスワードは8文字以上です')


class ForgotPasswordForm(Form):
    email = StringField('メール: ', validators=[DataRequired(), Email()])
    submit = SubmitField('パスワードを再設定する')

    def validate_email(self, field):
        if not User.select_user_by_email(field.data):
            ValidationError('メールアドレスが存在しません')


class UserForm(Form):
    email = StringField('メール: ', validators=[DataRequired(), Email('メールアドレスが誤っています')])
    username = StringField('ユーザ名: ', validators=[DataRequired()])
    picture_path = FileField('ファイルアップロード')
    submit = SubmitField('登録情報更新')

    def validate(self):
        if not super(Form, self).validate():
            return False
        user = User.select_user_by_email(self.email.data)
        if user:
            if user.id != int(current_user.get_id()):
                flash('そのメールアドレスは既に登録されています')
                return False
        return True


class ChangePasswordForm(Form):
    password = PasswordField(
        'パスワード: ',
        validators=[DataRequired(), EqualTo('confirm_password', message='パスワードが一致しません')]
    )
    confirm_password = PasswordField(
        'パスワード確認: ',
        validators=[DataRequired()]
    )
    submit = SubmitField('パスワードの更新')

    def validate_password(self, field):
        if len(field.data) < 8:
            raise ValidationError('パスワードは8文字以上です')


class UserSearchForm(Form):
    username = StringField('名前: ', validators=[DataRequired()])
    submit = SubmitField('ユーザ検索')


class ConnectForm(Form):
    connect_condition = HiddenField()
    to_user_id = HiddenField()
    submit = SubmitField()


class MessageForm(Form):
    to_user_id = HiddenField()
    message = TextAreaField()
    submit = SubmitField('メッセージを送信')

    def validate(self):
        if not super(Form, self).validate():
            return False
        is_friend = UserConnect.is_friend(self.to_user_id.data)
        if not is_friend:
            return False
        return True