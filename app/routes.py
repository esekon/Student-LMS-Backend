from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import User, Course, UserCourseProgress, CompletedChapter, StripeCustomer, Purchase
import stripe
import uuid
from flask_login import login_user, logout_user, login_required, current_user

main = Blueprint('main', __name__)
# Define your routes here

# User authentication routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        is_teacher = request.form.get('is_teacher', False)

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))

        new_user = User(email=email, password=generate_password_hash(password, method='sha256'), is_teacher=is_teacher)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# Course routes
@app.route('/courses')
def courses():
    courses = Course.query.all()
    return render_template('courses.html', courses=courses)

@app.route('/course/<string:course_id>')
def course_details(course_id):
    course = Course.query.get_or_404(course_id)
    user_progress = UserCourseProgress.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    completed_chapters = [chapter.chapter_id for chapter in user_progress.completed_chapters] if user_progress else []
    return render_template('course_details.html', course=course, completed_chapters=completed_chapters)

@app.route('/create-course', methods=['GET', 'POST'])
@login_required
def create_course():
    if not current_user.is_teacher:
        flash('You must be a teacher to create a course', 'danger')
        return redirect(url_for('courses'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        thumbnail = request.form.get('thumbnail')
        price = request.form.get('price')
        category_id = request.form.get('category_id')

        new_course = Course(id=str(uuid.uuid4()), title=title, description=description, image_url=thumbnail, price=float(price), teacher=current_user, category_id=category_id)
        db.session.add(new_course)
        db.session.commit()
        flash('Course created successfully', 'success')
        return redirect(url_for('courses'))

    categories = Category.query.all()
    return render_template('create_course.html', categories=categories)

@app.route('/edit-course/<string:course_id>', methods=['GET', 'POST'])
@login_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    if course.teacher != current_user:
        flash('You are not authorized to edit this course', 'danger')
        return redirect(url_for('courses'))

    if request.method == 'POST':
        course.title = request.form.get('title')
        course.description = request.form.get('description')
        course.image_url = request.form.get('thumbnail')
        course.price = float(request.form.get('price'))
        course.category_id = request.form.get('category_id')
        db.session.commit()
        flash('Course updated successfully', 'success')
        return redirect(url_for('course_details', course_id=course_id))

    categories = Category.query.all()
    return render_template('edit_course.html', course=course, categories=categories)

# Chapter routes
@app.route('/create-chapter/<string:course_id>', methods=['GET', 'POST'])
@login_required
def create_chapter(course_id):
    course = Course.query.get_or_404(course_id)
    if course.teacher != current_user:
        flash('You are not authorized to create chapters for this course', 'danger')
        return redirect(url_for('course_details', course_id=course_id))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        video_url = request.form.get('video_url')
        position = request.form.get('position')
        is_published = request.form.get('is_published', False)
        is_free = request.form.get('is_free', False)

        new_chapter = Chapter(id=str(uuid.uuid4()), title=title, description=description, video_url=video_url, position=int(position), is_published=is_published, is_free=is_free, course_id=course_id)
        db.session.add(new_chapter)
        db.session.commit()
        flash('Chapter created successfully', 'success')
        return redirect(url_for('course_details', course_id=course_id))

    return render_template('create_chapter.html', course=course)

@app.route('/edit-chapter/<string:chapter_id>', methods=['GET', 'POST'])
@login_required
def edit_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    course = chapter.course
    if course.teacher != current_user:
        flash('You are not authorized to edit this chapter', 'danger')
        return redirect(url_for('course_details', course_id=course.id))

    if request.method == 'POST':
        chapter.title = request.form.get('title')
        chapter.description = request.form.get('description')
        chapter.video_url = request.form.get('video_url')
        chapter.position = int(request.form.get('position'))
        chapter.is_published = request.form.get('is_published', False)
        chapter.is_free = request.form.get('is_free', False)
        db.session.commit()
        flash('Chapter updated successfully', 'success')
        return redirect(url_for('course_details', course_id=course.id))

    return render_template('edit_chapter.html', chapter=chapter, course=course)

@app.route('/mark-chapter-completed/<string:chapter_id>', methods=['POST'])
@login_required
def mark_chapter_completed(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    course = chapter.course
    user_progress = UserCourseProgress.query.filter_by(user_id=current_user.id, course_id=course.id).first()
    if not user_progress:
        user_progress = UserCourseProgress(user_id=current_user.id, course_id=course.id)
        db.session.add(user_progress)

    completed_chapter = CompletedChapter(chapter_id=chapter_id)
    user_progress.completed_chapters.append(completed_chapter)
    db.session.commit()
    return jsonify({'message': 'Chapter marked as completed'})

# Stripe integration
@app.route('/checkout', methods=['POST'])
def checkout():
    course_id = request.form.get('course_id')
    course = Course.query.get_or_404(course_id)

    customer = StripeCustomer.query.filter_by(user_id=current_user.id).first()
    if not customer:
        customer_data = stripe.Customer.create()
        new_customer = StripeCustomer(user_id=current_user.id, stripe_customer_id=customer_data.id)
        db.session.add(new_customer)
        db.session.commit()

    session = stripe.checkout.Session.create(
        customer=customer.stripe_customer_id,
        payment_method_types=['card'],
        line_items=[
            {
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': course.title,
                    },
                    'unit_amount': int(course.price * 100),
                },
                'quantity': 1,
            },
        ],
        mode='payment',
        success_url=url_for('success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=url_for('courses', _external=True),
    )

    return jsonify({'sessionId': session.id})

@app.route('/success')
def success():
    session_id = request.args.get('session_id')
    session = stripe.checkout.Session.retrieve(session_id)
    course_id = session.metadata.course_id
    course = Course.query.get(course_id)

    purchase = Purchase(user_id=current_user.id, course=course)
    db.session.add(purchase)
    db.session.commit()

    flash(f'You have purchased {course.title} successfully!', 'success')
    return redirect(url_for('dashboard'))
