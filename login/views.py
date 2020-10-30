from django.shortcuts import render, redirect, HttpResponse
from django.conf import settings
from django.core.cache import cache
import hashlib
import datetime
# Create your views here.
from . import models
from . import forms


def hash_code(s, salt='mysite'):
    h = hashlib.sha256()
    s += salt
    h.update(s.encode())
    return h.hexdigest()

def make_confirm_string(user):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    code = hash_code(user.name, now)
    models.ConfirmString.objects.create(code=code, user=user)
    return code

def send_mail(email, code):
    from django.core.mail import EmailMultiAlternatives

    subject = '来自www.likai.world的注册确认邮件'

    text_content = '''感谢注册www.likai.world，这里是李凯的博客和教程站点，专注于Python和Web的分享！\
                        如果你看到这条消息，说明你的邮箱服务器不提供HTML链接功能，请联系管理员！'''

    html_content = '''
                        <p>感谢注册<a href="http://{}/confirm/?code={}" target=blank>www.likai.world</a>，\
                        这里是李凯的博客和教程站点，专注于Python和Web的分享！</p>
                        <p>请点击站点链接完成注册确认！</p>
                        <p>此链接有效期为{}天！</p>
                        '''.format('127.0.0.1:8000', code, settings.CONFIRM_DAYS)

    msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()


def test_redis(request):
    # 存储数据
    cache.set("name", "tom", 20) # 该值的有效期为20s
    # 判断Redis中是否存在
    print(cache.has_kay("name"))  # 包含: true
    # 获取
    print(cache.get("name"))  # 返回: tom  无返回null
    return HttpResponse("测试Redis")


def index(request):
    if not request.session.get('is_login', None):
        return redirect('/login/')
    return render(request, 'login/index.html')


def login(request):
    if request.session.get('is_login', None):
        return redirect('/index/')
    if request.method == 'POST':
        login_form = forms.UserForm(request.POST)

        message = '请检查填写的内容！'
        if login_form.is_valid():
            username = login_form.cleaned_data.get('username')
            password = login_form.cleaned_data.get('password')
            try:
                user = models.User.objects.get(name=username)
            except:
                message = '用户不存在'
                return render(request, 'login/login.html', locals())

            if not user.has_confirmed:
                message = '该用户未进行邮件确认'
                return render(request, 'login/login.html', locals())

            if user.password == hash_code(password):
                request.session['is_login'] = True
                request.session['user_id'] = user.id
                request.session['user_name'] = user.name
                return redirect('/index/')
            else:
                message = '密码不正确'
                return render(request, 'login/login.html', locals())
        else:
            return render(request, 'login/login.html', locals())
    login_form = forms.UserForm()
    return render(request, 'login/login.html', locals())


def register(request):
    if request.session.get('is_login', None):
        return redirect('/index/')

    if request.method == 'POST':
        register_form = forms.RegisterForm(request.POST)
        message = '请检查填写的内容！'
        if register_form.is_valid():
            username = register_form.cleaned_data.get('username')
            password1 = register_form.cleaned_data.get('password1')
            password2 = register_form.cleaned_data.get('password2')
            email = register_form.cleaned_data.get('email')
            sex = register_form.cleaned_data.get('sex')

            if len(password1) < 8:
                message = '密码位数至少为8位'
                return render(request, 'login/register.html', locals())

            if not password1.isalnum() or password1.isdigit() or password1.isalpha():
                message = '密码应只包含数字与英文字母'
                return render(request, 'login/register.html', locals())

            if password1 != password2:
                message = '两次输入的密码不同'
                return render(request, 'login/register.html', locals())
            else:
                same_username = models.User.objects.filter(name=username)
                if same_username:
                    message = '用户名已存在'
                    return render(request, 'login/register.html', locals())
                same_email = models.User.objects.filter(email=email)
                if same_email:
                    message = '该邮箱已被使用'
                    return render(request, 'login/register.html', locals())

                new_user = models.User()
                new_user.name = username
                new_user.password = hash_code(password1)
                new_user.email = email
                new_user.sex = sex
                new_user.save()

                code = make_confirm_string(new_user)
                send_mail(email, code)

                message = '请前往邮箱进行确认！'
                return render(request, 'login/confirm.html', locals())
        else:
            return render(request, 'login/register.html', locals())

    register_form = forms.RegisterForm()
    return render(request, 'login/register.html', locals())


def logout(request):
    if not request.session.get('is_login', None):
        return redirect('/login/')
    request.session.flush()
    return redirect("/login/")

def user_confirm(request):
    code = request.GET.get('code', None)
    message = ''
    try:
        confirm = models.ConfirmString.objects.get(code=code)
    except:
        message = '无效的请求确认'
        return render(request, 'login/confirm.html', locals())

    c_time = confirm.c_time
    now = datetime.datetime.now()
    if now > c_time + datetime.timedelta(settings.CONFIRM_DAYS):
        confirm.user.delete()
        message = '您的邮件已过期！请重新注册！'
        return render(request, 'login/confirm.html', locals())
    else:
        confirm.user.has_confirmed = True
        confirm.user.save()
        confirm.delete()
        message = '感谢确认！请使用账号密码登录！'
        return render(request, 'login/confirm.html', locals())