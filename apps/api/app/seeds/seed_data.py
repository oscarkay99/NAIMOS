"""Demo seed data for NAIMOS Intelligence (sections 40-42).

Regions/districts/rivers/forest reserves use real, publicly known Ghanaian
geography (appropriate for public geographic features per section 40).
ALL incidents, field reports, evidence, and AI detections are synthetic
demo records (is_demo=True) with synthetic coordinates - never presented as
real NAIMOS operational data. Run with:

    python -m app.seeds.seed_data
"""

import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from geoalchemy2.shape import from_shape
from shapely.geometry import LineString, Point, Polygon
from sqlalchemy.orm import Session

from app.core.permissions import PERMISSIONS, ROLE_PERMISSIONS
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.ai import AIDetection, RiskFactor, RiskScore
from app.models.enums import (
    AIReviewStatus,
    DetectionType,
    EvidenceFileType,
    IncidentStatus,
    IncidentType,
    InvestigationStage,
    Priority,
    RiskCategory,
    RoleName,
    SourceType,
    VerificationStatus,
)
from app.models.evidence import Evidence, EvidenceVersion
from app.models.field_report import FieldReport
from app.models.geo import District, ForestReserve, ProtectedArea, Region, WaterBody
from app.models.incident import Incident, IncidentStatusHistory
from app.models.investigation import Assignment, Investigation, Officer, Team
from app.models.user import Permission, Role, User
from app.services.prediction.engine import persist_expansion_prediction
from app.services.risk.engine import calculate_risk
from app.services.storage.local_storage import get_storage_provider

DEMO_PASSWORD = "Demo@1234"

REGIONS = [
    ("Ahafo", "Goaso", 7.3600, -2.4500),
    ("Ashanti", "Kumasi", 6.6885, -1.6244),
    ("Bono", "Sunyani", 7.7386, -2.3237),
    ("Bono East", "Techiman", 7.7500, -1.9350),
    ("Central", "Cape Coast", 5.1053, -1.2466),
    ("Eastern", "Koforidua", 6.0940, -0.2591),
    ("Greater Accra", "Accra", 5.6037, -0.1870),
    ("North East", "Nalerigu", 10.5300, -0.3700),
    ("Northern", "Tamale", 9.4035, -0.8393),
    ("Oti", "Dambai", 8.0800, 0.1900),
    ("Savannah", "Damongo", 9.0833, -1.8167),
    ("Upper East", "Bolgatanga", 10.7856, -0.8390),
    ("Upper West", "Wa", 10.0601, -2.5099),
    ("Volta", "Ho", 6.6000, 0.4667),
    ("Western", "Sekondi-Takoradi", 4.8845, -1.7554),
    ("Western North", "Sefwi Wiawso", 6.2027, -2.6189),
]

DISTRICTS = {
    "Western": [
        ("Tarkwa-Nsuaem", "Tarkwa", 5.3006, -1.9932),
        ("Prestea Huni-Valley", "Bogoso", 5.4333, -2.1500),
        ("Wassa Amenfi West", "Asankragwa", 5.7667, -2.3667),
        ("Ellembelle", "Nkroful", 5.1667, -2.3833),
    ],
    "Western North": [
        ("Bibiani Anhwiaso Bekwai", "Bibiani", 6.4667, -2.3167),
        ("Juaboso", "Juaboso", 6.3667, -2.8167),
    ],
    "Ashanti": [
        ("Amansie West", "Manso Nkwanta", 6.3500, -1.9667),
        ("Obuasi Municipal", "Obuasi", 6.2027, -1.6738),
        ("Adansi South", "New Edubiase", 6.0500, -1.3500),
    ],
    "Eastern": [
        ("Birim North", "New Abirem", 6.2833, -0.9667),
        ("Atiwa West", "Kwabeng", 6.2333, -0.6333),
        ("Kwaebibirem", "Kade", 6.1500, -0.8667),
    ],
    "Central": [
        ("Upper Denkyira East", "Dunkwa-on-Offin", 5.9667, -1.7667),
        ("Twifo Atti-Morkwa", "Twifo Praso", 5.6500, -1.5500),
    ],
}

WATER_BODIES = [
    ("Ankobra River", "river", [(-2.3500, 5.2000), (-2.1000, 5.4500), (-1.9800, 5.6500)]),
    ("Pra River", "river", [(-1.9500, 5.8500), (-1.7500, 6.0500), (-1.5500, 5.9500)]),
    ("Offin River", "river", [(-1.8000, 5.9500), (-1.7000, 5.8000), (-1.6000, 5.6500)]),
    ("Birim River", "river", [(-0.9800, 6.3000), (-0.9000, 6.1000), (-0.8500, 5.9500)]),
    ("Densu River", "river", [(-0.4500, 5.9500), (-0.3500, 5.7500), (-0.2500, 5.6500)]),
]

PROTECTED_AREAS = [
    ("Bia Conservation Area", "national_park", -2.9800, 6.5300),
    ("Ankasa Conservation Area", "protected", -2.6300, 5.2700),
    ("Kakum National Park", "national_park", -1.3800, 5.3500),
]

FOREST_RESERVES = [
    ("Subri River Forest Reserve", -1.8800, 5.3800, 43800),
    ("Opon Mansi Forest Reserve", -2.0500, 5.5500, 15400),
    ("Tano Offin Forest Reserve", -1.7800, 6.4500, 40200),
    ("Bobiri Forest Reserve", -1.3300, 6.6900, 5400),
    ("Krokosua Hills Forest Reserve", -2.6800, 6.3500, 39600),
    ("Oda River Forest Reserve", -1.9450, 6.3150, 6900),
    ("Atiwa Range Forest Reserve", -0.6450, 6.2550, 25400),
]


def _square_polygon(lon: float, lat: float, half_size_deg: float = 0.04) -> Polygon:
    return Polygon([
        (lon - half_size_deg, lat - half_size_deg),
        (lon + half_size_deg, lat - half_size_deg),
        (lon + half_size_deg, lat + half_size_deg),
        (lon - half_size_deg, lat + half_size_deg),
        (lon - half_size_deg, lat - half_size_deg),
    ])


def seed_roles_and_permissions(db: Session) -> dict[str, Role]:
    permission_objs = {}
    for code, description in PERMISSIONS.items():
        perm = Permission(code=code, description=description)
        db.add(perm)
        permission_objs[code] = perm
    db.flush()

    role_objs: dict[str, Role] = {}
    for role_name, codes in ROLE_PERMISSIONS.items():
        role = Role(name=role_name.value, description=f"{role_name.value.replace('_', ' ').title()} role")
        role.permissions = [permission_objs[c] for c in codes]
        db.add(role)
        role_objs[role_name.value] = role
    db.flush()
    return role_objs


def seed_regions_and_districts(db: Session) -> tuple[dict[str, Region], dict[str, District]]:
    region_objs: dict[str, Region] = {}
    for name, capital, lat, lon in REGIONS:
        region = Region(name=name, capital=capital, centroid=from_shape(Point(lon, lat), srid=4326))
        db.add(region)
        region_objs[name] = region
    db.flush()

    district_objs: dict[str, District] = {}
    for region_name, districts in DISTRICTS.items():
        for name, capital, lat, lon in districts:
            district = District(
                region_id=region_objs[region_name].id, name=name, capital=capital,
                centroid=from_shape(Point(lon, lat), srid=4326),
            )
            db.add(district)
            district_objs[name] = district
    db.flush()
    return region_objs, district_objs


def seed_geo_features(db: Session) -> None:
    for name, water_type, coords in WATER_BODIES:
        db.add(WaterBody(name=name, water_type=water_type, geom=from_shape(LineString(coords), srid=4326)))

    for name, area_type, lon, lat in PROTECTED_AREAS:
        db.add(ProtectedArea(name=name, area_type=area_type, geom=from_shape(_square_polygon(lon, lat, 0.06), srid=4326)))

    for name, lon, lat, hectares in FOREST_RESERVES:
        db.add(ForestReserve(name=name, geom=from_shape(_square_polygon(lon, lat), srid=4326), area_hectares=hectares))
    db.flush()


def seed_users(db: Session, roles: dict[str, Role]) -> dict[str, User]:
    users_spec = [
        ("admin@naimos.gov.gh", "System Administrator", RoleName.SUPER_ADMIN.value, "A-001"),
        ("national.admin@naimos.gov.gh", "Ama Boateng", RoleName.NATIONAL_ADMIN.value, "A-002"),
        ("ops.manager@naimos.gov.gh", "Kwame Owusu", RoleName.OPERATIONS_MANAGER.value, "O-101"),
        ("supervisor@naimos.gov.gh", "Efua Mensah", RoleName.FIELD_SUPERVISOR.value, "S-201"),
        ("officer@naimos.gov.gh", "Kojo Asante", RoleName.FIELD_OFFICER.value, "F-301"),
        ("officer2@naimos.gov.gh", "Abena Darko", RoleName.FIELD_OFFICER.value, "F-302"),
        ("analyst@naimos.gov.gh", "Yaw Adjei", RoleName.INTELLIGENCE_ANALYST.value, "I-401"),
        ("env.analyst@naimos.gov.gh", "Akosua Frimpong", RoleName.ENVIRONMENTAL_ANALYST.value, "E-501"),
        ("pro@naimos.gov.gh", "Nana Yeboah", RoleName.PRO.value, "P-601"),
        ("viewer@naimos.gov.gh", "Report Viewer", RoleName.REPORT_VIEWER.value, "V-701"),
        ("auditor@naimos.gov.gh", "Kwabena Sarpong", RoleName.AUDITOR.value, "U-801"),
    ]
    user_objs: dict[str, User] = {}
    for email, full_name, role_name, badge in users_spec:
        user = User(
            email=email, full_name=full_name, hashed_password=hash_password(DEMO_PASSWORD),
            role_id=roles[role_name].id, badge_number=badge, is_active=True,
        )
        db.add(user)
        user_objs[email] = user
    db.flush()
    return user_objs


def seed_teams_and_officers(db: Session, regions: dict[str, Region], users: dict[str, User]) -> dict[str, Team]:
    team_a = Team(name="Team Alpha (Western)", region_id=regions["Western"].id)
    team_b = Team(name="Team Bravo (Ashanti)", region_id=regions["Ashanti"].id)
    db.add_all([team_a, team_b])
    db.flush()

    db.add_all([
        Officer(user_id=users["officer@naimos.gov.gh"].id, team_id=team_a.id, rank="Field Officer"),
        Officer(user_id=users["officer2@naimos.gov.gh"].id, team_id=team_b.id, rank="Field Officer"),
        Officer(user_id=users["supervisor@naimos.gov.gh"].id, team_id=team_a.id, rank="Supervisor"),
    ])
    db.flush()
    return {"Team Alpha (Western)": team_a, "Team Bravo (Ashanti)": team_b}


def _make_incident(
    db: Session, ref_suffix: str, title: str, description: str, lat: float, lon: float,
    region: Region, district: District, incident_type: IncidentType, status: IncidentStatus,
    verification_status: VerificationStatus, water_body_affected: bool, protected_area_affected: bool,
    created_by: User, days_ago: int, priority: Priority = Priority.MEDIUM,
) -> Incident:
    created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    incident = Incident(
        reference_number=f"NAIMOS-2026-{ref_suffix}",
        title=title, description=description,
        location=from_shape(Point(lon, lat), srid=4326), latitude=lat, longitude=lon,
        region_id=region.id, district_id=district.id,
        incident_type=incident_type, source_type=SourceType.FIELD_REPORT,
        status=status, verification_status=verification_status, priority=priority,
        water_body_affected=water_body_affected, protected_area_affected=protected_area_affected,
        equipment_observed="2 excavators, 1 water pump" if incident_type == IncidentType.SUSPECTED_ILLEGAL_MINING else None,
        estimated_people_present=random.randint(3, 15),
        is_demo=True, created_by=created_by.id, created_at=created_at, updated_at=created_at,
    )
    db.add(incident)
    db.flush()
    return incident


def seed_incidents(db: Session, regions, districts, users) -> list[Incident]:
    officer = users["officer@naimos.gov.gh"]
    officer2 = users["officer2@naimos.gov.gh"]
    analyst = users["analyst@naimos.gov.gh"]
    incidents: list[Incident] = []

    # Scenario 1: suspected hotspot near a water body (Ankobra River, Tarkwa-Nsuaem)
    i1 = _make_incident(
        db, "000101", "Suspected mining activity near Ankobra River",
        "AI-detected land disturbance and a field report both indicate suspected illegal mining "
        "activity within 400m of the Ankobra River.",
        5.3200, -2.2270, regions["Western"], districts["Tarkwa-Nsuaem"],
        IncidentType.SUSPECTED_ILLEGAL_MINING, IncidentStatus.FIELD_VERIFICATION_REQUIRED,
        VerificationStatus.PENDING_VERIFICATION, True, False, officer, days_ago=3, priority=Priority.HIGH,
    )
    incidents.append(i1)

    # Scenario 2: existing hotspot expands - older + newer report near the same location
    i2a = _make_incident(
        db, "000102", "Initial report - land clearing observed",
        "Community report of vegetation clearing consistent with early-stage mining preparation.",
        5.4400, -2.1600, regions["Western"], districts["Prestea Huni-Valley"],
        IncidentType.VEGETATION_LOSS, IncidentStatus.UNDER_REVIEW,
        VerificationStatus.UNVERIFIED, False, False, officer, days_ago=45,
    )
    i2b = _make_incident(
        db, "000103", "Follow-up report - expanded excavation observed",
        "Second report at the same location indicates the excavation area has expanded "
        "significantly since the first report.",
        5.4420, -2.1580, regions["Western"], districts["Prestea Huni-Valley"],
        IncidentType.LAND_DISTURBANCE, IncidentStatus.UNDER_REVIEW,
        VerificationStatus.UNVERIFIED, False, False, officer, days_ago=4, priority=Priority.HIGH,
    )
    incidents.extend([i2a, i2b])

    # Scenario 6: field verification changes incident status - full lifecycle
    i6 = _make_incident(
        db, "000104", "Verified illegal mining site - Amansie West",
        "Field team confirmed active excavation with heavy equipment approximately 600m from "
        "forest reserve boundary.",
        6.3200, -1.9500, regions["Ashanti"], districts["Amansie West"],
        IncidentType.SUSPECTED_ILLEGAL_MINING, IncidentStatus.VERIFIED,
        VerificationStatus.VERIFIED, False, True, officer2, days_ago=10, priority=Priority.CRITICAL,
    )
    incidents.append(i6)
    for previous, new, reason, days_ago in [
        (None, IncidentStatus.NEW, "Incident created", 10),
        (IncidentStatus.NEW, IncidentStatus.UNDER_REVIEW, "Assigned for analyst review", 9),
        (IncidentStatus.UNDER_REVIEW, IncidentStatus.FIELD_VERIFICATION_REQUIRED, "Risk score elevated - field visit required", 8),
        (IncidentStatus.FIELD_VERIFICATION_REQUIRED, IncidentStatus.VERIFIED, "Field verification completed", 2),
    ]:
        db.add(IncidentStatusHistory(
            incident_id=i6.id, previous_status=previous, new_status=new, changed_by=officer2.id,
            reason=reason, changed_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
        ))

    # Repeated recent reports + one historical report clustered near i1 so the
    # Ankobra River location becomes a genuine HIGH-risk demo hotspot with a
    # rich, explainable factor breakdown (section 3 / section 43 demo flow).
    cluster = [
        ("000114", "Second field report - same hotspot", "Community report corroborates excavator activity at the same site.",
         5.3215, -2.2255, "Western", "Tarkwa-Nsuaem", IncidentType.SUSPECTED_ILLEGAL_MINING,
         IncidentStatus.NEW, VerificationStatus.UNVERIFIED, True, False, 1, Priority.HIGH),
        ("000115", "Third field report - same hotspot", "Additional observation of continued excavation near the river.",
         5.3190, -2.2285, "Western", "Tarkwa-Nsuaem", IncidentType.LAND_DISTURBANCE,
         IncidentStatus.NEW, VerificationStatus.UNVERIFIED, True, False, 2, Priority.HIGH),
        ("000116", "Fourth field report - same hotspot",
         "Repeated observation, activity appears ongoing. Officer also noted a new access road cut "
         "through the treeline toward the riverbank since the last visit.",
         5.3225, -2.2240, "Western", "Tarkwa-Nsuaem", IncidentType.SUSPECTED_ILLEGAL_MINING,
         IncidentStatus.NEW, VerificationStatus.UNVERIFIED, True, False, 3, Priority.HIGH),
        ("000117", "Historical report - same area", "Older report retained to establish activity history for this location.",
         5.3180, -2.2300, "Western", "Tarkwa-Nsuaem", IncidentType.OTHER,
         IncidentStatus.CLOSED, VerificationStatus.UNVERIFIED, True, False, 60, Priority.LOW),
    ]
    for ref, title, desc, lat, lon, region_name, district_name, itype, status, vstatus, water, protected, days_ago, priority in cluster:
        inc = _make_incident(
            db, ref, title, desc, lat, lon, regions[region_name], districts[district_name],
            itype, status, vstatus, water, protected, officer, days_ago, priority,
        )
        incidents.append(inc)

    # Additional variety across regions/districts for the map + analytics demo
    extra = [
        ("000105", "Report near Birim River", "Community report of water discoloration and equipment noise.",
         6.2600, -0.9610, "Eastern", "Birim North", IncidentType.WATER_POLLUTION,
         IncidentStatus.NEW, VerificationStatus.UNVERIFIED, True, False, 1, Priority.MEDIUM),
        ("000106", "Unauthorized equipment reported - Obuasi", "Excavator observed operating without visible permit signage.",
         6.1900, -1.6900, "Ashanti", "Obuasi Municipal", IncidentType.UNAUTHORIZED_EQUIPMENT,
         IncidentStatus.UNDER_REVIEW, VerificationStatus.UNVERIFIED, False, False, 6, Priority.MEDIUM),
        ("000107", "Land disturbance near Offin River", "AI change detection flagged exposed soil near river bend.",
         5.9200, -1.7830, "Central", "Upper Denkyira East", IncidentType.LAND_DISTURBANCE,
         IncidentStatus.FIELD_VERIFICATION_REQUIRED, VerificationStatus.PENDING_VERIFICATION, True, False, 2, Priority.HIGH),
        ("000108", "Closed case - no activity confirmed", "Field verification found no evidence of mining activity.",
         6.2600, -0.6500, "Eastern", "Atiwa West", IncidentType.OTHER,
         IncidentStatus.CLOSED, VerificationStatus.REJECTED, False, True, 20, Priority.LOW),
        ("000109", "Vegetation clearing - Wassa Amenfi West", "Satellite-proxy signal indicates new clearing pattern.",
         5.7800, -2.3800, "Western", "Wassa Amenfi West", IncidentType.VEGETATION_LOSS,
         IncidentStatus.NEW, VerificationStatus.UNVERIFIED, False, False, 0, Priority.MEDIUM),
        ("000110", "Historical case - Adansi South", "Older resolved case retained for historical trend analysis.",
         6.0600, -1.3600, "Ashanti", "Adansi South", IncidentType.SUSPECTED_ILLEGAL_MINING,
         IncidentStatus.CLOSED, VerificationStatus.VERIFIED, False, False, 90, Priority.MEDIUM),
    ]
    for ref, title, desc, lat, lon, region_name, district_name, itype, status, vstatus, water, protected, days_ago, priority in extra:
        inc = _make_incident(
            db, ref, title, desc, lat, lon, regions[region_name], districts[district_name],
            itype, status, vstatus, water, protected, analyst, days_ago, priority,
        )
        incidents.append(inc)

    db.flush()
    return incidents


def seed_status_history_for_new(db: Session, incidents: list[Incident], users: dict[str, User]) -> None:
    """Every incident needs at least a creation history row (skip i6 which
    already has a full custom history above)."""
    officer = users["officer@naimos.gov.gh"]
    for incident in incidents:
        existing = db.query(IncidentStatusHistory).filter_by(incident_id=incident.id).count()
        if existing:
            continue
        db.add(IncidentStatusHistory(
            incident_id=incident.id, previous_status=None, new_status=IncidentStatus.NEW,
            changed_by=officer.id, reason="Incident created", changed_at=incident.created_at,
        ))
    db.flush()


def seed_risk_scores(db: Session, incidents: list[Incident]) -> None:
    """Seeds today's risk score for every incident, plus a synthetic
    ~8-day-old snapshot so the Risk Leaderboard's week-over-week Change%
    column has real history to compute from out of the box (section 3 /
    the 'AI Risk Map' leaderboard). The historical score is deterministic
    per incident (reference-number-seeded) rather than random noise, so
    re-seeding always produces the same demo story."""
    for incident in incidents:
        result = calculate_risk(db, incident.latitude, incident.longitude, exclude_incident_id=incident.id)
        now = datetime.now(timezone.utc)
        risk = RiskScore(
            incident_id=incident.id, location=incident.location, score=result.score, category=result.category,
            calculated_at=now, explanation=result.explanation,
        )
        db.add(risk)
        db.flush()
        for f in result.factors:
            db.add(RiskFactor(risk_score_id=risk.id, label=f.label, points=f.points, detail=f.detail))
        incident.risk_score = result.score

        rng = random.Random(incident.reference_number)
        change_factor = rng.uniform(-0.05, 0.5)
        past_score = max(1, min(100, round(result.score / (1 + change_factor))))
        db.add(RiskScore(
            incident_id=incident.id, location=incident.location, score=past_score,
            category=RiskCategory.from_score(past_score), calculated_at=now - timedelta(days=8),
            explanation=f"RISK SCORE: {past_score} ({RiskCategory.from_score(past_score).value}). "
                        "Historical snapshot from prior monitoring pass.",
        ))
    db.flush()


def seed_expansion_predictions(db: Session, incidents: list[Incident]) -> None:
    """Seeds today's expansion prediction for every incident (Predictive
    Galamsey Intelligence). Must run after seed_risk_scores (reuses the
    8-day-old risk history for the trend signal) and after
    seed_ai_detections (reuses the seeded NEW_ROAD / land-disturbance
    signals) so the demo shows real, non-trivial predictions out of the
    box rather than every location scoring 0%."""
    now = datetime.now(timezone.utc)
    for incident in incidents:
        persist_expansion_prediction(db, incident, calculated_at=now)
    db.flush()


def seed_ai_detections(db: Session, incidents: list[Incident], users: dict[str, User]) -> None:
    analyst = users["env.analyst@naimos.gov.gh"]
    target = incidents[0]

    # Scenario 8: AI detects a potential anomaly (pending review)
    db.add(AIDetection(
        location=target.location, detection_type=DetectionType.EXCAVATION, confidence=0.84,
        estimated_area_hectares=4.8, observation_date=datetime.now(timezone.utc) - timedelta(days=2),
        previous_observation_date=datetime.now(timezone.utc) - timedelta(days=32),
        incident_id=target.id, requires_verification=True, review_status=AIReviewStatus.PENDING,
    ))
    db.add(AIDetection(
        location=target.location, detection_type=DetectionType.EXPOSED_SOIL, confidence=0.72,
        estimated_area_hectares=3.1, observation_date=datetime.now(timezone.utc) - timedelta(days=1),
        incident_id=target.id, requires_verification=True, review_status=AIReviewStatus.PENDING,
    ))

    # New access route near the same Tarkwa-Nsuaem hotspot - feeds the
    # Predictive Galamsey Intelligence "new access route detected" signal.
    db.add(AIDetection(
        location=target.location, detection_type=DetectionType.NEW_ROAD, confidence=0.81,
        observation_date=datetime.now(timezone.utc) - timedelta(days=3),
        incident_id=target.id, requires_verification=True, review_status=AIReviewStatus.PENDING,
    ))

    # Scenario 9: human rejects an AI detection (false positive)
    db.add(AIDetection(
        location=incidents[1].location, detection_type=DetectionType.EXPOSED_SOIL, confidence=0.61,
        estimated_area_hectares=1.2, observation_date=datetime.now(timezone.utc) - timedelta(days=15),
        incident_id=incidents[1].id, requires_verification=True, review_status=AIReviewStatus.REJECTED,
        reviewed_by=analyst.id, reviewed_at=datetime.now(timezone.utc) - timedelta(days=14),
    ))

    db.add(AIDetection(
        location=incidents[2].location, detection_type=DetectionType.VEGETATION_LOSS, confidence=0.77,
        estimated_area_hectares=6.3, observation_date=datetime.now(timezone.utc) - timedelta(days=5),
        incident_id=incidents[2].id, requires_verification=True, review_status=AIReviewStatus.PENDING,
    ))
    db.flush()


def seed_field_reports(db: Session, incidents: list[Incident], users: dict[str, User]) -> None:
    officer = users["officer@naimos.gov.gh"]
    target = incidents[0]

    transcript = (
        "We arrived at the location around 10:30 in the morning and observed two excavators "
        "operating close to the river. The operators left when the team arrived."
    )
    db.add(FieldReport(
        incident_id=target.id, officer_id=officer.id, location=target.location,
        narrative=transcript, transcript=transcript,
        ai_extraction={
            "time_mentioned": "10:30", "equipment_mentioned": ["2 excavators"],
            "water_body_mentioned": "Nearby river", "activity_summary": "Suspected mining-related activity",
            "status": "Requires verification",
        },
        officer_approved=True, officer_approved_at=datetime.now(timezone.utc) - timedelta(days=3),
    ))
    db.flush()


def seed_evidence(db: Session, incidents: list[Incident], users: dict[str, User]) -> None:
    """Creates a small real placeholder file on disk so download/hash flows work end to end in the demo."""
    officer = users["officer@naimos.gov.gh"]
    storage = get_storage_provider()
    target = incidents[0]

    placeholder_note = (
        b"NAIMOS DEMO EVIDENCE PLACEHOLDER\n"
        b"This stands in for a field photo in the demo environment.\n"
        b"In production this would be an actual JPEG/MP4 upload.\n"
    )
    relative_path, file_hash, size = storage.save(f"incidents/{target.id}", "demo-site-photo.txt", placeholder_note)

    evidence = Evidence(
        incident_id=target.id, uploaded_by=officer.id, file_type=EvidenceFileType.IMAGE,
        original_filename="demo-site-photo.txt", file_path=relative_path, file_hash=file_hash,
        file_size_bytes=size, location=target.location, captured_at=datetime.now(timezone.utc) - timedelta(days=3),
        description="Demo placeholder for a field-captured site photo.",
        ai_analysis={
            "detections": [
                {"label": "Excavator", "confidence": 0.91},
                {"label": "Exposed soil", "confidence": 0.88},
            ],
            "model_name": "mock-llm", "model_version": "0.1.0-demo",
        },
        verification_status=VerificationStatus.PENDING_VERIFICATION,
    )
    db.add(evidence)
    db.flush()
    db.add(EvidenceVersion(
        evidence_id=evidence.id, version_number=1, file_path=relative_path, file_hash=file_hash,
        uploaded_by=officer.id, reason="Initial upload",
    ))
    db.flush()


def seed_investigations(db: Session, incidents: list[Incident], teams: dict[str, Team], users: dict[str, User]) -> None:
    supervisor = users["supervisor@naimos.gov.gh"]
    officer = users["officer@naimos.gov.gh"]
    target = incidents[0]

    investigation = Investigation(
        incident_id=target.id, stage=InvestigationStage.FIELD_VERIFICATION, lead_officer_id=officer.id,
        opened_at=datetime.now(timezone.utc) - timedelta(days=3),
        summary="Field verification in progress following AI-flagged land disturbance near Ankobra River.",
    )
    db.add(investigation)
    db.flush()

    db.add(Assignment(
        investigation_id=investigation.id, priority=Priority.HIGH, assigned_team_id=teams["Team Alpha (Western)"].id,
        assigned_officer_id=officer.id, assigned_by=supervisor.id,
        deadline=(datetime.now(timezone.utc) + timedelta(days=4)).date(), status="ACTIVE",
        notes="Prioritize due to proximity to Ankobra River.",
    ))

    verified = incidents[3]  # i6, the verified Amansie West case
    inv2 = Investigation(
        incident_id=verified.id, stage=InvestigationStage.RESOLUTION,
        lead_officer_id=users["officer2@naimos.gov.gh"].id,
        opened_at=datetime.now(timezone.utc) - timedelta(days=10),
        closed_at=datetime.now(timezone.utc) - timedelta(days=2),
        summary="Field-verified active mining site; evidence collected and escalated.",
    )
    db.add(inv2)
    db.flush()
    db.add(Assignment(
        investigation_id=inv2.id, priority=Priority.CRITICAL, assigned_team_id=teams["Team Bravo (Ashanti)"].id,
        assigned_officer_id=users["officer2@naimos.gov.gh"].id, assigned_by=supervisor.id,
        deadline=(datetime.now(timezone.utc) - timedelta(days=3)).date(), status="COMPLETED",
        notes="Verified and closed.",
    ))
    db.flush()


def run() -> None:
    db: Session = SessionLocal()
    try:
        print("Seeding roles and permissions...")
        roles = seed_roles_and_permissions(db)

        print("Seeding regions and districts...")
        regions, districts = seed_regions_and_districts(db)

        print("Seeding water bodies, protected areas, forest reserves...")
        seed_geo_features(db)

        print("Seeding demo users...")
        users = seed_users(db, roles)

        print("Seeding teams and officers...")
        teams = seed_teams_and_officers(db, regions, users)

        print("Seeding demo incidents...")
        incidents = seed_incidents(db, regions, districts, users)
        seed_status_history_for_new(db, incidents, users)

        print("Seeding AI detections...")
        seed_ai_detections(db, incidents, users)

        print("Calculating risk scores...")
        seed_risk_scores(db, incidents)

        print("Calculating expansion predictions...")
        seed_expansion_predictions(db, incidents)

        print("Seeding field reports (voice-to-report demo)...")
        seed_field_reports(db, incidents, users)

        print("Seeding evidence...")
        seed_evidence(db, incidents, users)

        print("Seeding investigations and assignments...")
        seed_investigations(db, incidents, teams, users)

        db.commit()
        print("\nSeed complete.")
        print(f"Demo login password for all seeded users: {DEMO_PASSWORD}")
        print("Example: admin@naimos.gov.gh / officer@naimos.gov.gh / pro@naimos.gov.gh / analyst@naimos.gov.gh")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
