"""Hospital-specific Diabetic Retinopathy screening analytics service."""

from typing import Dict, Any, List
from collections import defaultdict
from datetime import datetime

from src.database.connection import Database
from src.core.constants import GRADE_LABELS, GRADE_SEVERITY


class AnalyticsService:
    """Computes tenant-isolated screening metrics, DR stage distribution, and trends."""

    def __init__(self, db: Database):
        self.db = db

    def get_hospital_analytics(self, tenant_id: str) -> Dict[str, Any]:
        """Calculates comprehensive DR screening performance metrics for a hospital."""
        with self.db.session() as conn:
            # 1. Total Patients
            pat_count_row = conn.execute(
                "SELECT COUNT(*) as c FROM patients WHERE tenant_id = ?",
                (tenant_id,)
            ).fetchone()
            total_patients = pat_count_row["c"] if pat_count_row else 0

            # 2. Total Screenings
            scr_count_row = conn.execute(
                "SELECT COUNT(*) as c FROM screenings WHERE tenant_id = ?",
                (tenant_id,)
            ).fetchone()
            total_screenings = scr_count_row["c"] if scr_count_row else 0

            # 3. Grade Distribution
            grade_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
            rows = conn.execute(
                "SELECT grade, COUNT(*) as c FROM screenings WHERE tenant_id = ? GROUP BY grade",
                (tenant_id,)
            ).fetchall()
            for r in rows:
                g = r["grade"]
                if g in grade_counts:
                    grade_counts[g] = r["c"]

            # Severity distribution formatted
            severity_distribution = [
                {
                    "grade": g,
                    "label": GRADE_LABELS.get(g, f"Grade {g}"),
                    "severity": GRADE_SEVERITY.get(g, "Unknown"),
                    "count": grade_counts[g],
                    "percentage": round((grade_counts[g] / total_screenings * 100), 1) if total_screenings > 0 else 0.0,
                }
                for g in range(5)
            ]

            # 4. Positivity Rate (Grades 1-4)
            positive_count = sum(grade_counts[g] for g in (1, 2, 3, 4))
            positivity_rate = round((positive_count / total_screenings * 100), 1) if total_screenings > 0 else 0.0

            # 5. Urgent Referrals (Grades 3 & 4)
            urgent_count = grade_counts[3] + grade_counts[4]
            urgent_rate = round((urgent_count / total_screenings * 100), 1) if total_screenings > 0 else 0.0

            # 6. Diabetes Type Distribution among patients
            diabetes_type_counts = {}
            d_rows = conn.execute(
                "SELECT diabetes_type, COUNT(*) as c FROM patients WHERE tenant_id = ? GROUP BY diabetes_type",
                (tenant_id,)
            ).fetchall()
            for r in d_rows:
                diabetes_type_counts[r["diabetes_type"]] = r["c"]

            # 7. Monthly Trends (most recent 12 months in chronological order)
            trend_rows = conn.execute(
                """
                SELECT month, c, positive
                FROM (
                    SELECT strftime('%Y-%m', created_at) as month,
                           COUNT(*) as c,
                           SUM(CASE WHEN grade >= 1 THEN 1 ELSE 0 END) as positive
                    FROM screenings
                    WHERE tenant_id = ?
                    GROUP BY month
                    ORDER BY month DESC
                    LIMIT 12
                )
                ORDER BY month ASC
                """,
                (tenant_id,)
            ).fetchall()

            monthly_trends = [
                {
                    "month": r["month"] or "Recent",
                    "total": r["c"],
                    "positive": r["positive"] or 0,
                }
                for r in trend_rows
            ]

            # 8. Recent Urgent / High-Risk Screenings (Distinct Latest per Patient)
            urgent_rows = conn.execute(
                """
                SELECT id, patient_id, grade, diagnosis, confidence, severity,
                       created_at, first_name, last_name, age, phone
                FROM (
                    SELECT s.id, s.patient_id, s.grade, s.diagnosis, s.confidence, s.severity,
                           s.created_at, p.first_name, p.last_name, p.age, p.phone,
                           ROW_NUMBER() OVER (
                               PARTITION BY s.patient_id 
                               ORDER BY s.created_at DESC, s.rowid DESC
                           ) as rn
                    FROM screenings s
                    JOIN patients p ON s.patient_id = p.id
                    WHERE s.tenant_id = ? AND s.grade >= 3
                )
                WHERE rn = 1
                ORDER BY created_at DESC
                LIMIT 5
                """,
                (tenant_id,)
            ).fetchall()

            urgent_cases = [
                {
                    "screening_id": r["id"],
                    "patient_id": r["patient_id"],
                    "patient_name": f"{r['first_name']} {r['last_name']}",
                    "age": r["age"],
                    "phone": r["phone"],
                    "grade": r["grade"],
                    "diagnosis": r["diagnosis"],
                    "confidence": r["confidence"],
                    "severity": r["severity"],
                    "date": r["created_at"],
                }
                for r in urgent_rows
            ]

            return {
                "tenant_id": tenant_id,
                "total_patients": total_patients,
                "total_screenings": total_screenings,
                "positive_count": positive_count,
                "positivity_rate": positivity_rate,
                "urgent_count": urgent_count,
                "urgent_rate": urgent_rate,
                "severity_distribution": severity_distribution,
                "diabetes_types": diabetes_type_counts,
                "monthly_trends": monthly_trends,
                "urgent_cases": urgent_cases,
            }

