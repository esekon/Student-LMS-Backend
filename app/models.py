from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    is_teacher = db.Column(db.Boolean, default=False)
    courses_purchased = db.relationship('Course', secondary='user_courses', backref='students')
    courses_created = db.relationship('Course', backref='teacher', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.email}>'

class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.Text)
    price = db.Column(db.Float)
    is_published = db.Column(db.Boolean, default=False)
    category_id = db.Column(db.String(36), db.ForeignKey('categories.id'))
    category = db.relationship('Category', backref='courses')
    teacher_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    teacher = db.relationship('User', backref='courses_created', lazy='dynamic')
    chapters = db.relationship('Chapter', backref='course', cascade='all, delete-orphan')
    attachments = db.relationship('Attachment', backref='course', cascade='all, delete-orphan')
    purchases = db.relationship('Purchase', backref='course', cascade='all, delete-orphan')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Course {self.title}>'

class Chapter(db.Model):
    __tablename__ = 'chapters'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    video_url = db.Column(db.Text)
    position = db.Column(db.Integer, nullable=False)
    is_published = db.Column(db.Boolean, default=False)
    is_free = db.Column(db.Boolean, default=False)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'), nullable=False)
    mux_data = db.relationship('MuxData', backref='chapter', uselist=False, cascade='all, delete-orphan')
    user_progress = db.relationship('UserProgress', backref='chapter', cascade='all, delete-orphan')
    attachments = db.relationship('Attachment', backref='chapter', lazy='dynamic')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Chapter {self.title}>'

class Attachment(db.Model):
    __tablename__ = 'attachments'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = db.Column(db.String(100), nullable=False)
    url = db.Column(db.Text, nullable=False)
    chapter_id = db.Column(db.String(36), db.ForeignKey('chapters.id'), nullable=False)

    def __repr__(self):
        return f'<Attachment {self.filename}>'

user_courses = db.Table('user_courses',
    db.Column('user_id', db.String(36), db.ForeignKey('users.id'), primary_key=True),
    db.Column('course_id', db.String(36), db.ForeignKey('courses.id'), primary_key=True)
)

class UserCourseProgress(db.Model):
    __tablename__ = 'user_course_progress'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'), nullable=False)
    completed_chapters = db.relationship('CompletedChapter', backref='user_course_progress', lazy='dynamic')

    def __repr__(self):
        return f'<UserCourseProgress {self.user_id} - {self.course_id}>'

class CompletedChapter(db.Model):
    __tablename__ = 'completed_chapters'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_course_progress_id = db.Column(db.String(36), db.ForeignKey('user_course_progress.id'), nullable=False)
    chapter_id = db.Column(db.String(36), db.ForeignKey('chapters.id'), nullable=False)

    def __repr__(self):
        return f'<CompletedChapter {self.chapter_id}>'

class Purchase(db.Model):
    __tablename__ = 'purchases'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), nullable=False)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'course_id', name='unique_user_course'),
    )

    def __repr__(self):
        return f'<Purchase {self.id}>'

class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False, unique=True)
    courses = db.relationship('Course', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'

class StripeCustomer(db.Model):
    __tablename__ = 'stripe_customers'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, unique=True)
    stripe_customer_id = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<StripeCustomer {self.stripe_customer_id}>'