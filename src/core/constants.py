"""Core constants and clinical definitions for Diabetic Retinopathy Detection."""

NUM_CLASSES = 5

# Standard Clinical Diabetic Retinopathy Severity Scale (ICDR / APTOS 2019)
GRADE_LABELS = {
    0: "No Diabetic Retinopathy",
    1: "Mild DR",
    2: "Moderate DR",
    3: "Severe DR",
    4: "Proliferative DR",
}

GRADE_SEVERITY = {
    0: "None",
    1: "Mild",
    2: "Moderate",
    3: "Severe",
    4: "Critical",
}

GRADE_COLORS = {
    0: "#22c55e",  # Green
    1: "#84cc16",  # Lime
    2: "#f59e0b",  # Amber
    3: "#f97316",  # Orange
    4: "#ef4444",  # Red
}

GRADE_RECOMMENDATIONS = {
    0: "No signs of diabetic retinopathy detected. Routine annual screening recommended.",
    1: "Mild non-proliferative DR detected (microaneurysms only). Optimise blood sugar and blood pressure control. Re-screen in 12 months.",
    2: "Moderate non-proliferative DR detected. Refer to ophthalmologist. Re-screen in 6 months.",
    3: "Severe non-proliferative DR detected (extensive intraretinal hemorrhages). Urgent ophthalmology referral required within 4 weeks.",
    4: "Proliferative DR detected (neovascularization or vitreous hemorrhage). Immediate ophthalmology referral required. High risk of vision loss.",
}

# ImageNet normalization statistics
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

