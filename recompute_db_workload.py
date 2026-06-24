import os
import sys

sys.path.append(os.getcwd())

from database import SessionLocal
from models import ProductivityRecord


def compute_estimated_completion_time(expected_workload_hours, video_duration):
    video_duration_hours = float(video_duration) if video_duration is not None else 0.0
    completion_hours = max(expected_workload_hours, video_duration_hours)
    days = int(completion_hours // 8)
    hours = int(completion_hours % 8)
    day_str = f"{days} day{'s' if days != 1 else ''}"
    hour_str = f"{hours} hour{'s' if hours != 1 else ''}"

    if days > 0 and hours > 0:
        return f"{day_str} {hour_str}"
    if days > 0:
        return day_str
    return hour_str


def main():
    session = SessionLocal()
    try:
        records = session.query(ProductivityRecord).all()
        updated = 0
        for r in records:
            base_hours = 10.0
            multiplier = 1.0 + (r.cameras_used - 1) * 0.5
            expected_workload_hours = base_hours * multiplier
            estimated_completion_time = compute_estimated_completion_time(expected_workload_hours, r.video_duration)

            if (r.expected_workload_hours is None or abs(r.expected_workload_hours - expected_workload_hours) > 1e-6) or r.estimated_completion_time != estimated_completion_time:
                r.expected_workload_hours = expected_workload_hours
                r.estimated_completion_time = estimated_completion_time
                updated += 1

        session.commit()
        print(f"Processed {len(records)} records, updated {updated} records.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
