from flask import Flask, render_template, request
from flask_wtf import FlaskForm
from wtforms import StringField, RadioField
from wtforms.validators import InputRequired, length, regexp
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import json
import random

app = Flask(__name__)
app.secret_key = "L33T133713371337L33T"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///base.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CSRF_ENABLED = True
WTF_CSRF_SECRET_KEY = 'L33T133713371337L33T'

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Подгружаем из json данные
with open("teachers.json") as f:
    teachers_json = json.load(f)

with open("goals.json") as f:
    goals = json.load(f)

days = {"mon": "Понедельник", "tue": "Вторник", "wed": "Среда", "thu": "Четверг", "fri": "Пятница",
        "sat": "Суббота", "sun": "Воскресенье"}

teachers_goals_association = db.Table(
    "teachers_goals",
    db.Column("teacher_id", db.Integer, db.ForeignKey("teachers.id")),
    db.Column("goal_id", db.Integer, db.ForeignKey("goals.id")),
)


# Иницилиазирую классы бд
class Teacher(db.Model):
    __tablename__ = "teachers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    about = db.Column(db.String, nullable=False)
    rating = db.Column(db.Float)
    picture = db.Column(db.String)
    price = db.Column(db.Float)
    email = db.Column(db.String, nullable=False)
    free = db.Column(db.String, nullable=False)
    bookings = db.relationship("Booking")
    goals = db.relationship(
        "Goal", secondary=teachers_goals_association, back_populates="teachers"
    )


class Booking(db.Model):
    __tablename__ = "booking"
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String, nullable=False)
    hour = db.Column(db.Integer, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False)
    teacher = db.relationship("Teacher", nullable=False)
    name = db.Column(db.String, nullable=False)
    phone = db.Column(db.String, nullable=False)


class Request(db.Model):
    __tablename__ = "request"
    id = db.Column(db.Integer, primary_key=True)
    hour = db.Column(db.String)
    name = db.Column(db.String, nullable=False)
    goal_id = db.Column(db.Integer, db.ForeignKey("goals.id"))
    goal = db.relationship("Goal")
    phone = db.Column(db.String, nullable=False)


class Goal(db.Model):
    __tablename__ = "goals"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    alias = db.Column(db.String, nullable=False)
    teachers = db.relationship(
        "Teacher", secondary=teachers_goals_association, back_populates="goals"
    )


class RequestForm(FlaskForm):
    goals_list = []
    for goal, name in goals.items():
        goals_list.append((goal, name))
    goal = RadioField("Цель занятий?", choices=goals_list,
                      validators=[InputRequired("Выберите цель занятий!")])
    free_time = RadioField("Сколько готовы уделять?", choices=[("1-2 часа в неделю", "1-2 часа в неделю"),
                                                               ("3-5 часов в неделю", "3-5 часов в неделю"),
                                                               ("5-7 часов в неделю", "5-7 часов в неделю"),
                                                               ("7-10 часов в неделю", "7-10 часов в неделю")],
                           validators=[InputRequired("Выберите свободное время!")])

    name = StringField("Вас зовут", validators=[InputRequired("Введите своё имя!"),
                                                length(min=2, message="Имя не может быть меньше 2 символов!")])

    # regexp https://wtforms.readthedocs.io/en/stable/_modules/wtforms/validators/#Regexp
    phone = StringField("Ваш телефон", validators=[InputRequired("Введите ваш номер!"),
                                                   regexp(
                                                       "^((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{7,10}$",
                                                       message="Некорректный номер телефона!")])


class BookingForm(FlaskForm):
    client_name = StringField("Ваше имя", validators=[InputRequired("Введите своё имя!"),
                                                      length(min=3,
                                                             message="Имя не может быть меньше 2 символов!")])
    client_phone = StringField("Ваш номер телефона", validators=[InputRequired("Введите свой номер телефона!"),
                                                                 regexp(
                                                                     "^((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{7,"
                                                                     "10}$",
                                                                     message="Вы ввели некорректный номер телефона!")])


def update_requests(goal, free_time, name, phone):
    req = Request(
        name=name,
        hour=free_time,
        goal=db.session.query(Goal).filter(Goal.alias == goal).first(),
        phone=phone
    )
    db.session.add(req)
    db.session.commit()


def update_bookings(teacher_id, name, phone, weekday, time):
    time, _ = time.split(':')
    booking = Booking(
        day=weekday,
        name=name,
        hour=time,
        phone=phone,
        teacher=db.session.query(Teacher).get(teacher_id)
    )
    db.session.add(booking)
    db.session.commit()


if db.session.query(Goal).count() == 0:
    for goal in goals:
        db.session.add(Goal(name=goals[goal], alias=goal))
    db.session.commit()
    goals_db = db.session.query(Goal).all()
    goals_list = {}
    for goal in goals_db:
        goals_list[goal.alias] = goal

    for teacher in teachers_json:
        t = Teacher(
            name=teacher['name'],
            about=teacher['about'],
            rating=teacher['rating'],
            picture=teacher['picture'],
            price=teacher['price'],
            free=json.dumps(teacher['free'])
        )
        for goal in teacher['goals']:
            t.goals.append(goals_list[goal])
        db.session.add(t)
    db.session.commit()


@app.route("/")
def main():
    teachers_all = db.session.query(Teacher).all()
    return render_template("index.html", goals=goals, teachers=random.sample(teachers_all, 6))


@app.route("/all/")
def all_teachers():
    # здесь просто выводим главную страничку без обреза списка учителей
    teachers_all = db.session.query(Teacher).all()
    return render_template("index.html", goals=goals, teachers=teachers_all)


@app.route("/goals/<goal>/")
def goals_page(goal):
    teachers = db.session.query(Teacher).order_by(Teacher.rating.desc()).all()
    teachers_goal = list()
    for teacher in teachers:
        if goal in teacher["goals"]:
            teachers_goal.append(teacher)
    return render_template("goal.html", goals=goals, goal=goal, teachers=teachers_goal)


@app.route("/request/", methods=["GET", "POST"])
def request_view():
    form = RequestForm()
    if request.method == "POST":
        if form.validate_on_submit():
            goal = goals[form.goal.data]
            free_time = form.free_time.data
            name = form.name.data
            phone = form.phone.data
            update_requests(goal, free_time, name, phone)
            return render_template("request_done.html", goal=goal, free_time=free_time, name=name, phone=phone)
    return render_template("request.html", form=form)


@app.route("/request_done/")
def request_done():
    pass


@app.route("/profile/<int:teacher_id>/")
def profile_teacher(teacher_id):
    teachers = db.session.query(Teacher).order_by(Teacher.rating.desc()).all()
    for teacher_name in teachers:
        if teacher_name["id"] == teacher_id:
            teacher = teacher_name
    return render_template("profile.html", days=days, goals=goals, teacher=teacher)


@app.route("/booking/<int:teacher_id>/<day>/<time>/", methods=["GET", "POST"])
def booking_form(teacher_id, day, time):
    teachers = db.session.query(Teacher).order_by(Teacher.rating.desc()).all()
    time = time[0:-2] + time[-2:].replace("00", ":00")
    for teacher_name in teachers:
        if teacher_name["id"] == teacher_id:
            teacher = teacher_name
    form = BookingForm()
    if request.method == "POST":
        if form.validate_on_submit():
            client_name = form.client_name.data
            client_phone = form.client_phone.data
            update_bookings(teacher_id, client_name, client_phone, day, time)
            return render_template("booking_done.html", client_name=client_name, client_phone=client_phone,
                                   client_weekday=days[day], client_time=time)
    return render_template("booking.html", form=form, day=day, dayname=days[day], time=time, teacher_id=teacher_id,
                           teacher=teacher)


@app.errorhandler(404)
def render_not_found(error):
    return "Ничего не нашлось! Вот неудача, отправляйтесь на главную!"


@app.errorhandler(500)
def render_server_error(error):
    return "Что-то не так, но мы все починим"


if __name__ == '__main__':
    app.run(debug=True)
