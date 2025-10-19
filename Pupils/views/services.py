from django.db.models import F, ExpressionWrapper, FloatField, Value
from django.db.models.functions import Coalesce

from ..models import Marks

# Subject maps
lower_subject_map = {
    "Mathematics": "mathematics",
    "English": "english",
    "Kiswahili": "kiswahili",
    "Environmental Activities": "environmental_activities",
    "Integrated Creative": "integrated_creative",
    "Cre": "cre",
}
upper_subject_map = {
    "Mathematics": "mathematics",
    "English": "english",
    "Kiswahili": "kiswahili",
    "Science & Technology": "science_technology",
    "SST/CRE": "sst_cre",
    "Agriculture & Nutrition": "agri_nutrition",
    "Creative Arts": "creative_arts",
    "Cre": "cre",
}
junior_subject_map = {
    "Mathematics": "mathematics",
    "English": "english",
    "Kiswahili": "kiswahili",
    "SST/CRE": "sst_cre",
    "Agriculture & Nutrition": "agri_nutrition",
    "Creative Arts": "creative_arts",
    "Pretech/Bs/Comps": "pretech_bs_computer",
    "Integrated Science": "integrated_science",
    "Cre": "cre",
}

lower_grades = ["PP 1", "PP 2", "Grade 1", "Grade 2", "Grade 3"]
upper_grades = ["Grade 4", "Grade 5", "Grade 6"]
junior_grades = ["Grade 7", "Grade 8", "Grade 9"]


def _build_expression(subject_map):
    """Builds an expression that sums all subject columns, using Coalesce to avoid NULLs."""
    expr = None
    
    for col in subject_map.values():
        col_expr = Coalesce(F(col), Value(0))
        expr = col_expr if expr is None else expr + col_expr
    return expr


def update_marks(school_id, year=None, term=None, exam_type=None):
    """
    Updates total_marks and mean_marks for Marks table.

    Args:
        alias: database alias (per school DB).
        year: optional filter for year.
        term: optional filter for term.
        exam_type: optional filter for exam type.
    """
    filters = {}
    if year:
        filters["year"] = year
    if term:
        filters["term"] = term
    if exam_type:
        filters["type_of_exam"] = exam_type

    # Lower grades
    expr = _build_expression(lower_subject_map)
    sst_cre = ((Coalesce(f'cre',0) + Coalesce('social_studies',0))/30)* 100
    Marks.objects.filter(school = school_id, **filters).update(
        total_marks=expr,sst_cre = sst_cre,
        mean_marks=ExpressionWrapper(expr / len(lower_subject_map), output_field=FloatField()),
    )

    # Upper grades
    expr = _build_expression(upper_subject_map)
    sst_cre = ((Coalesce(f'cre',0) + Coalesce('social_studies',0))/30)* 100
    Marks.objects.filter(school = school_id, **filters).update(
        total_marks=expr,sst_cre = sst_cre,
        mean_marks=ExpressionWrapper(expr / len(upper_subject_map), output_field=FloatField()),
    )

    # Junior grades
    expr = _build_expression(junior_subject_map)
    Marks.objects.filter(school = school_id, **filters).update(
        total_marks=expr,sst_cre = sst_cre,
        mean_marks=ExpressionWrapper(expr / len(junior_subject_map), output_field=FloatField()),
    )
def compute_average(model,school_id,year,term,):
    from django.db.models import Avg, Value
    from django.db.models.functions import Coalesce

    averages = (
        model.objects
        .filter(term=term, year=year)
        .annotate(score_nonnull=Coalesce('score', Value(0)))
        .values('student', 'sub_strand')
        .annotate(avg_score=Avg('score_nonnull'))
    )

    for entry in averages:
        student_id = entry['student']
        subject = entry['sub_strand']
        avg_score = entry['avg_score'] or 0

        mark = Marks.objects.filter(
            school_id = school_id,
            registration_no=student_id,
            term=term,
            year=year
        ).first()

        if not mark:
            continue  # skip students without marks record

        # Only update if subject column exists in Marks model
        if hasattr(mark, subject):
            setattr(mark, subject, avg_score)
            mark.save(update_fields=[subject])

