from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import Course, Chapter, Attachment
from . import db, utils
import mux_python
import stripe

courses_bp = Blueprint('courses', __name__)

@courses_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_teacher:
        courses = current_user.courses_created.all()
    else:
        courses = current_user.courses_purchased

    return render_template('courses/dashboard.html', courses=courses)

@courses_bp.route('/courses')
def courses_list():
    courses = Course.query.all()
    return render_template('courses/list.html', courses=courses)

@courses_bp.route('/courses/<int:course_id>')
def course_details(course_id):
    course = Course.query.get_or_404(course_id)
    return render_template('courses/details.html', course=course)

@courses_bp.route('/courses/new', methods=['GET', 'POST'])
@login_required
def create_course():
    if not current_user.is_teacher:
        flash('Only teachers can create courses', 'danger')
        return redirect(url_for('courses.dashboard'))

    form = CreateCourseForm()

    if form.validate_on_submit():
        title = form.title.data
        description = form.description.data
        price = form.price.data
        thumbnail = form.thumbnail.data

        thumbnail_filename = utils.save_file(thumbnail.data, 'thumbnails')
        new_course = Course(
            title=title,
            description=description,
            price=price,
            thumbnail=thumbnail_filename,
            teacher=current_user
        )

        db.session.add(new_course)
        db.session.commit()

        flash('Course created successfully', 'success')
        return redirect(url_for('courses.dashboard'))

    return render_template('courses/create.html', form=form)

@courses_bp.route('/courses/<int:course_id>/new-chapter', methods=['GET', 'POST'])
@login_required
def create_chapter(course_id):
    course = Course.query.get_or_404(course_id)

    if course.teacher != current_user:
        flash('You are not authorized to modify this course', 'danger')
        return redirect(url_for('courses.course_details', course_id=course_id))

    form = CreateChapterForm()

    if form.validate_on_submit():
        title = form.title.data
        description = form.description.data  # Rich text content
        video = form.video.data
        position = form.position.data

        if not title or not description or not video or not position:
            flash('Please fill in all fields', 'danger')
        else:
            video_filename = utils.save_file(video.data, 'videos')
            video_url = utils.upload_to_mux(video_filename)

            new_chapter = Chapter(
                title=title,
                description=description,
                video_url=video_url,
                position=position,
                course=course
            )

            db.session.add(new_chapter)
            db.session.commit()

            flash('Chapter created successfully', 'success')
            return redirect(url_for('courses.course_details', course_id=course_id))

    return render_template('courses/create_chapter.html', form=form, course=course)

@courses_bp.route('/courses/<int:course_id>/chapters/<int:chapter_id>/attachments', methods=['POST'])
@login_required
def upload_attachment(course_id, chapter_id):
    course = Course.query.get_or_404(course_id)
    chapter = Chapter.query.get_or_404(chapter_id)

    if course.teacher != current_user:
        flash('You are not authorized to modify this course', 'danger')
        return redirect(url_for('courses.course_details', course_id=course_id))

    attachment = request.files.get('attachment')

    if attachment:
        attachment_filename = utils.save_file(attachment, 'attachments')
        new_attachment = Attachment(
            filename=attachment_filename,
            chapter=chapter
        )

        db.session.add(new_attachment)
        db.session.commit()

        flash('Attachment uploaded successfully', 'success')
    else:
        flash('No attachment provided', 'danger')

    return redirect(url_for('courses.course_details', course_id=course_id))


def upload_to_mux(filename):
    client = mux_python.VideoAssetClient(
        mux_token_id=app.config['MUX_TOKEN_ID'],
        mux_token_secret=app.config['MUX_TOKEN_SECRET']
    )

    asset = client.create_asset(
        input=f"{app.config['UPLOAD_FOLDER']}/videos/{filename}",
        playback_policy=[
            mux_python.PlaybackPolicy.PUBLIC
        ]
    )

    return asset.playback_ids[0].url


import stripe

@courses_bp.route('/courses/<int:course_id>/purchase', methods=['POST'])
@login_required
def purchase_course(course_id):
    course = Course.query.get_or_404(course_id)

    if course in current_user.courses_purchased:
        flash('You have already purchased this course', 'info')
        return redirect(url_for('courses.course_details', course_id=course_id))

    stripe.api_key = app.config['STRIPE_SECRET_KEY']

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': course.title,
                },
                'unit_amount': int(course.price * 100),  # Stripe uses cents
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=url_for('courses.checkout_success', course_id=course_id, _external=True),
        cancel_url=url_for('courses.checkout_cancel', course_id=course_id, _external=True),
    )

    return redirect(session.url, code=303)

@courses_bp.route('/courses/<int:course_id>/checkout/success')
@login_required
def checkout_success(course_id):
    course = Course.query.get_or_404(course_id)
    current_user.courses_purchased.append(course)
    db.session.commit()

    flash('Course purchased successfully', 'success')
    return redirect(url_for('courses.course_details', course_id=course_id))

@courses_bp.route('/courses/<int:course_id>/checkout/cancel')
@login_required
def checkout_cancel(course_id):
    flash('Payment cancelled', 'info')
    return redirect(url_for('courses.course_details', course_id=course_id))


@courses_bp.route('/courses/<int:course_id>/progress', methods=['POST'])
@login_required
def toggle_chapter_completion(course_id):
    course = Course.query.get_or_404(course_id)
    chapter_id = request.form.get('chapter_id')
    chapter = Chapter.query.get(chapter_id)

    if chapter is None or chapter.course != course:
        flash('Invalid chapter', 'danger')
        return redirect(url_for('courses.course_details', course_id=course_id))

    user_course_progress = UserCourseProgress.query.filter_by(user=current_user, course=course).first()

    if user_course_progress is None:
        user_course_progress = UserCourseProgress(user=current_user, course=course)
        db.session.add(user_course_progress)

    completed_chapter = CompletedChapter.query.filter_by(user_course_progress=user_course_progress, chapter=chapter).first()

    if completed_chapter:
        db.session.delete(completed_chapter)
        db.session.commit()
        flash(f'Chapter {chapter.title} marked as incomplete', 'info')
    else:
        new_completed_chapter = CompletedChapter(user_course_progress=user_course_progress, chapter=chapter)
        db.session.add(new_completed_chapter)
        db.session.commit()
        flash(f'Chapter {chapter.title} marked as complete', 'success')

    return redirect(url_for('courses.course_details', course_id=course_id))

@courses_bp.route('/courses/<int:course_id>/progress')
@login_required
def course_progress(course_id):
    course = Course.query.get_or_404(course_id)
    user_course_progress = UserCourseProgress.query.filter_by(user=current_user, course=course).first()

    if user_course_progress is None:
        return jsonify({'progress': 0})

    completed_chapters_count = user_course_progress.completed_chapters.count()
    total_chapters_count = course.chapters.count()

    progress = int((completed_chapters_count / total_chapters_count) * 100)
    return jsonify({'progress': progress})


@courses_bp.route('/courses/<int:course_id>/chapters/reorder', methods=['POST'])
@login_required
def reorder_chapters(course_id):
    course = Course.query.get_or_404(course_id)

    if course.teacher != current_user:
        flash('You are not authorized to modify this course', 'danger')
        return redirect(url_for('courses.course_details', course_id=course_id))

    chapter_ids = request.form.getlist('chapter_ids[]')

    for position, chapter_id in enumerate(chapter_ids, start=1):
        chapter = Chapter.query.get(chapter_id)
        if chapter and chapter.course == course:
            chapter.position = position
            db.session.commit()

    flash('Chapter positions updated successfully', 'success')
    return redirect(url_for('courses.course_details', course_id=course_id))