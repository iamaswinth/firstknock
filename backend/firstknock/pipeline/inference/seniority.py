import structlog
from firstknock.pipeline.graph.queries import GET_TOTAL_EXPERIENCE_MONTHS, SET_PERSON_SENIORITY

logger = structlog.get_logger()


def compute_seniority(total_months: int) -> str:
    if total_months < 12:
        return "junior"
    elif total_months < 36:
        return "mid"
    elif total_months < 72:
        return "senior"
    else:
        return "staff"


async def write_seniority(session, user_id: str) -> str:
    result = await session.run(GET_TOTAL_EXPERIENCE_MONTHS, person_id=user_id)
    row = await result.single()
    total_months = int(row["total_months"] or 0) if row else 0

    seniority = compute_seniority(total_months)
    await session.run(
        SET_PERSON_SENIORITY,
        person_id=user_id,
        seniority=seniority,
        total_months=total_months,
    )
    logger.info("seniority_written", person_id=user_id, seniority=seniority, total_months=total_months)
    return seniority
