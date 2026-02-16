"""Travel & Logistics Planner testleri."""

import pytest

from app.core.travel import (
    FlightFinder,
    HotelComparator,
    ItineraryBuilder,
    TransferPlanner,
    TravelDocumentManager,
    TravelExpenseTracker,
    TravelOrchestrator,
    TravelPriceAlertSetter,
    VisaRequirementChecker,
)
from app.models.travel_models import (
    BookingStatus,
    DocumentType,
    ExpenseCategory,
    FlightRecord,
    HotelRating,
    HotelRecord,
    ItineraryRecord,
    TransportType,
    TravelExpenseRecord,
    VisaStatus,
)


# ── Models ──────────────────────────────────────


class TestTravelModels:
    """Travel model testleri."""

    def test_transport_type_values(self):
        assert TransportType.flight == "flight"
        assert TransportType.train == "train"
        assert TransportType.bus == "bus"
        assert TransportType.car_rental == "car_rental"
        assert TransportType.taxi == "taxi"
        assert TransportType.shuttle == "shuttle"

    def test_booking_status_values(self):
        assert BookingStatus.pending == "pending"
        assert BookingStatus.confirmed == "confirmed"
        assert BookingStatus.cancelled == "cancelled"
        assert BookingStatus.completed == "completed"
        assert BookingStatus.refunded == "refunded"
        assert BookingStatus.waitlisted == "waitlisted"

    def test_visa_status_values(self):
        assert VisaStatus.not_required == "not_required"
        assert VisaStatus.required == "required"
        assert VisaStatus.applied == "applied"
        assert VisaStatus.approved == "approved"
        assert VisaStatus.denied == "denied"

    def test_expense_category_values(self):
        assert ExpenseCategory.flight == "flight"
        assert ExpenseCategory.hotel == "hotel"
        assert ExpenseCategory.transport == "transport"
        assert ExpenseCategory.food == "food"
        assert ExpenseCategory.activity == "activity"
        assert ExpenseCategory.shopping == "shopping"
        assert ExpenseCategory.insurance == "insurance"
        assert ExpenseCategory.other == "other"

    def test_document_type_values(self):
        assert DocumentType.passport == "passport"
        assert DocumentType.visa == "visa"
        assert DocumentType.insurance == "insurance"
        assert DocumentType.booking == "booking"
        assert DocumentType.ticket == "ticket"
        assert DocumentType.receipt == "receipt"

    def test_hotel_rating_values(self):
        assert HotelRating.budget == "budget"
        assert HotelRating.luxury == "luxury"

    def test_flight_record(self):
        r = FlightRecord(
            origin="IST", destination="LHR", price=300.0
        )
        assert r.origin == "IST"
        assert r.destination == "LHR"
        assert r.price == 300.0
        assert len(r.flight_id) == 8

    def test_hotel_record(self):
        r = HotelRecord(
            name="Grand", city="London", price_per_night=150.0
        )
        assert r.name == "Grand"
        assert r.city == "London"

    def test_itinerary_record(self):
        r = ItineraryRecord(
            destination="Paris", days=5
        )
        assert r.destination == "Paris"
        assert r.days == 5
        assert r.status == "draft"

    def test_expense_record(self):
        r = TravelExpenseRecord(
            category="food", amount=25.0
        )
        assert r.category == "food"
        assert r.amount == 25.0
        assert r.currency == "USD"


# ── FlightFinder ───────────────────────────────


class TestFlightFinder:
    """FlightFinder testleri."""

    def setup_method(self):
        self.ff = FlightFinder()

    def test_init(self):
        assert self.ff.flight_count == 0

    def test_search_flights(self):
        r = self.ff.search_flights(
            origin="IST", destination="LHR"
        )
        assert r["searched"] is True
        assert r["result_count"] == 3
        assert r["origin"] == "IST"

    def test_search_business_class(self):
        r = self.ff.search_flights(
            cabin_class="business", passengers=2
        )
        assert r["searched"] is True
        prices = [
            f["price"] for f in r["results"]
        ]
        assert all(p > 0 for p in prices)

    def test_compare_prices(self):
        flights = [
            {"airline": "A", "price": 300},
            {"airline": "B", "price": 200},
            {"airline": "C", "price": 500},
        ]
        r = self.ff.compare_prices(flights)
        assert r["compared"] is True
        assert r["cheapest"]["price"] == 200
        assert r["savings"] == 300

    def test_compare_prices_empty(self):
        r = self.ff.compare_prices([])
        assert r["compared"] is True
        assert r["cheapest"] is None

    def test_optimize_route_cheapest(self):
        r = self.ff.optimize_route(
            origin="IST", destination="LHR",
            prefer="cheapest",
        )
        assert r["optimized"] is True
        assert r["recommended"]["type"] == "connecting"

    def test_optimize_route_fastest(self):
        r = self.ff.optimize_route(
            origin="IST", destination="LHR",
            prefer="fastest",
        )
        assert r["recommended"]["type"] == "direct"

    def test_analyze_layover_short(self):
        r = self.ff.analyze_layover(
            layover_city="FRA", layover_hours=0.5
        )
        assert r["analyzed"] is True
        assert r["risk"] == "high"
        assert r["recommendation"] == "too_short"

    def test_analyze_layover_comfortable(self):
        r = self.ff.analyze_layover(
            layover_hours=3.0
        )
        assert r["risk"] == "low"
        assert r["recommendation"] == "comfortable"
        assert "lounge_access" in r["activities"]

    def test_analyze_layover_long(self):
        r = self.ff.analyze_layover(
            layover_hours=7.0
        )
        assert r["recommendation"] == "long_wait"
        assert "city_tour" in r["activities"]

    def test_create_booking(self):
        r = self.ff.create_booking(
            airline="THY", price=300.0, passengers=2
        )
        assert r["booked"] is True
        assert r["total_price"] == 600.0
        assert r["status"] == "confirmed"


# ── HotelComparator ────────────────────────────


class TestHotelComparator:
    """HotelComparator testleri."""

    def setup_method(self):
        self.hc = HotelComparator()

    def test_init(self):
        assert self.hc.hotel_count == 0

    def test_search_hotels(self):
        r = self.hc.search_hotels(
            city="Istanbul", nights=3
        )
        assert r["searched"] is True
        assert r["result_count"] == 3

    def test_search_hotels_max_price(self):
        r = self.hc.search_hotels(
            city="London", max_price=100.0
        )
        assert r["searched"] is True
        for h in r["results"]:
            assert h["price_per_night"] <= 100.0

    def test_track_price_drop(self):
        r = self.hc.track_price(
            hotel_name="Grand",
            current_price=100.0,
            previous_price=150.0,
        )
        assert r["tracked"] is True
        assert r["trend"] == "significant_drop"

    def test_track_price_stable(self):
        r = self.hc.track_price(
            current_price=100.0,
            previous_price=100.0,
        )
        assert r["trend"] == "stable"

    def test_track_price_increase(self):
        r = self.hc.track_price(
            current_price=200.0,
            previous_price=150.0,
        )
        assert r["trend"] == "significant_increase"

    def test_aggregate_reviews_empty(self):
        r = self.hc.aggregate_reviews()
        assert r["aggregated"] is True
        assert r["avg_rating"] == 0.0

    def test_aggregate_reviews(self):
        reviews = [
            {"rating": 5}, {"rating": 4},
            {"rating": 3}, {"rating": 2},
        ]
        r = self.hc.aggregate_reviews(reviews)
        assert r["avg_rating"] == 3.5
        assert r["sentiment"] == "good"
        assert r["positive"] == 2

    def test_aggregate_reviews_excellent(self):
        reviews = [
            {"rating": 5}, {"rating": 5}, {"rating": 4},
        ]
        r = self.hc.aggregate_reviews(reviews)
        assert r["sentiment"] == "excellent"

    def test_filter_amenities_match(self):
        r = self.hc.filter_amenities(
            required=["wifi", "pool"],
            hotel_amenities=["wifi", "pool", "gym"],
        )
        assert r["filtered"] is True
        assert r["meets_criteria"] is True
        assert r["match_pct"] == 100.0

    def test_filter_amenities_missing(self):
        r = self.hc.filter_amenities(
            required=["wifi", "pool", "spa"],
            hotel_amenities=["wifi"],
        )
        assert r["meets_criteria"] is False

    def test_score_location_excellent(self):
        r = self.hc.score_location(
            distance_center_km=1.0,
            distance_airport_km=10.0,
            nearby_restaurants=5,
            public_transport=True,
        )
        assert r["scored"] is True
        assert r["grade"] == "excellent"

    def test_score_location_poor(self):
        r = self.hc.score_location(
            distance_center_km=20.0,
            distance_airport_km=50.0,
        )
        assert r["grade"] == "poor"


# ── TransferPlanner ────────────────────────────


class TestTransferPlanner:
    """TransferPlanner testleri."""

    def setup_method(self):
        self.tp = TransferPlanner()

    def test_init(self):
        assert self.tp.transfer_count == 0

    def test_plan_ground_transport(self):
        r = self.tp.plan_ground_transport(
            origin="Hotel", destination="Airport",
            distance_km=20.0,
        )
        assert r["planned"] is True
        assert r["option_count"] == 3

    def test_plan_airport_transfer(self):
        r = self.tp.plan_airport_transfer(
            airport="IST", hotel="Grand Hotel",
            distance_km=40.0, passengers=2,
        )
        assert r["planned"] is True
        assert r["recommended"] == "public_bus"

    def test_find_car_rental_economy(self):
        r = self.tp.find_car_rental(
            city="Antalya", days=5,
            car_type="economy",
        )
        assert r["found"] is True
        assert r["daily_rate"] == 35.0
        assert r["total_rental"] == 175.0

    def test_find_car_rental_suv(self):
        r = self.tp.find_car_rental(
            car_type="suv", days=3,
        )
        assert r["daily_rate"] == 100.0

    def test_check_public_transit_excellent(self):
        r = self.tp.check_public_transit(
            city="Istanbul",
            has_metro=True, has_bus=True,
            has_tram=True,
        )
        assert r["checked"] is True
        assert r["coverage"] == "excellent"
        assert r["mode_count"] == 3

    def test_check_public_transit_none(self):
        r = self.tp.check_public_transit(
            has_metro=False, has_bus=False,
            has_tram=False,
        )
        assert r["coverage"] == "none"

    def test_optimize_costs(self):
        options = [
            {"type": "taxi", "price": 50.0},
            {"type": "bus", "price": 5.0},
            {"type": "shuttle", "price": 20.0},
        ]
        r = self.tp.optimize_costs(options)
        assert r["optimized"] is True
        assert r["cheapest"]["price"] == 5.0
        assert r["potential_savings"] == 45.0

    def test_optimize_costs_empty(self):
        r = self.tp.optimize_costs([])
        assert r["optimized"] is True
        assert r["cheapest"] is None


# ── VisaRequirementChecker ─────────────────────


class TestVisaRequirementChecker:
    """VisaRequirementChecker testleri."""

    def setup_method(self):
        self.vrc = VisaRequirementChecker()

    def test_init(self):
        assert self.vrc.application_count == 0

    def test_check_visa_free(self):
        r = self.vrc.check_requirements(
            passport_country="TR",
            destination="GE",
            stay_days=14,
        )
        assert r["checked"] is True
        assert r["visa_required"] is False
        assert r["visa_type"] == "visa_free"

    def test_check_visa_required_tourist(self):
        r = self.vrc.check_requirements(
            passport_country="TR",
            destination="US",
            stay_days=14,
        )
        assert r["visa_required"] is True
        assert r["visa_type"] == "tourist"

    def test_check_visa_long_stay(self):
        r = self.vrc.check_requirements(
            passport_country="TR",
            destination="DE",
            stay_days=120,
        )
        assert r["visa_type"] == "long_stay"

    def test_get_document_checklist_tourist(self):
        r = self.vrc.get_document_checklist("tourist")
        assert r["generated"] is True
        assert "valid_passport" in r["documents"]
        assert "hotel_reservation" in r["documents"]

    def test_get_document_checklist_business(self):
        r = self.vrc.get_document_checklist("business")
        assert "company_letter" in r["documents"]

    def test_estimate_processing_tourist(self):
        r = self.vrc.estimate_processing_time("tourist")
        assert r["estimated"] is True
        assert r["estimated_days"] == 10
        assert r["urgency"] == "low"

    def test_estimate_processing_long(self):
        r = self.vrc.estimate_processing_time("long_stay")
        assert r["estimated_days"] == 30
        assert r["urgency"] == "high"

    def test_track_application(self):
        r = self.vrc.track_application(
            destination="US", visa_type="tourist",
        )
        assert r["tracked"] is True
        assert self.vrc.application_count == 1

    def test_check_deadlines_overdue(self):
        r = self.vrc.check_deadlines(
            travel_days_away=10,
            processing_days=15,
        )
        assert r["checked"] is True
        assert r["alert"] == "overdue"
        assert r["severity"] == "critical"

    def test_check_deadlines_on_track(self):
        r = self.vrc.check_deadlines(
            travel_days_away=60,
            processing_days=15,
        )
        assert r["alert"] == "on_track"
        assert r["severity"] == "low"

    def test_check_deadlines_urgent(self):
        r = self.vrc.check_deadlines(
            travel_days_away=18,
            processing_days=15,
        )
        assert r["alert"] == "urgent"


# ── ItineraryBuilder ───────────────────────────


class TestItineraryBuilder:
    """ItineraryBuilder testleri."""

    def setup_method(self):
        self.ib = ItineraryBuilder()

    def test_init(self):
        assert self.ib.itinerary_count == 0

    def test_create_itinerary(self):
        r = self.ib.create_itinerary(
            destination="Paris", days=3,
        )
        assert r["created"] is True
        assert r["days"] == 3
        assert len(r["day_plans"]) == 3
        assert r["total_activities"] > 0

    def test_create_cultural(self):
        r = self.ib.create_itinerary(
            style="cultural", days=2,
        )
        assert r["created"] is True

    def test_add_activity(self):
        itn = self.ib.create_itinerary(
            destination="Rome", days=2,
        )
        r = self.ib.add_activity(
            itinerary_id=itn["itinerary_id"],
            day=1, time="15:00",
            activity="museum_visit",
        )
        assert r["added"] is True

    def test_add_activity_not_found(self):
        r = self.ib.add_activity(
            itinerary_id="invalid", day=1,
        )
        assert r["added"] is False

    def test_add_activity_day_not_found(self):
        itn = self.ib.create_itinerary(days=1)
        r = self.ib.add_activity(
            itinerary_id=itn["itinerary_id"],
            day=99,
        )
        assert r["added"] is False

    def test_optimize_route(self):
        activities = [
            {"time": "14:00", "activity": "B", "duration_h": 2},
            {"time": "09:00", "activity": "A", "duration_h": 3},
        ]
        r = self.ib.optimize_route(activities)
        assert r["optimized"] is True
        assert r["activities"][0]["activity"] == "A"
        assert r["total_hours"] == 5

    def test_optimize_route_empty(self):
        r = self.ib.optimize_route([])
        assert r["count"] == 0

    def test_check_time_balanced(self):
        r = self.ib.check_time_management(
            planned_hours=7.0,
            available_hours=12.0,
        )
        assert r["checked"] is True
        assert r["status"] == "balanced"

    def test_check_time_overbooked(self):
        r = self.ib.check_time_management(
            planned_hours=11.0,
            available_hours=12.0,
        )
        assert r["status"] == "overbooked"

    def test_check_time_relaxed(self):
        r = self.ib.check_time_management(
            planned_hours=3.0,
            available_hours=12.0,
        )
        assert r["status"] == "relaxed"

    def test_handle_flexibility_strict(self):
        r = self.ib.handle_flexibility(
            flexibility_level="strict"
        )
        assert r["configured"] is True
        assert r["buffer_minutes"] == 0
        assert r["allow_alternatives"] is False

    def test_handle_flexibility_flexible(self):
        r = self.ib.handle_flexibility(
            flexibility_level="flexible"
        )
        assert r["buffer_minutes"] == 60
        assert r["allow_alternatives"] is True


# ── TravelPriceAlertSetter ─────────────────────


class TestTravelPriceAlertSetter:
    """TravelPriceAlertSetter testleri."""

    def setup_method(self):
        self.pas = TravelPriceAlertSetter()

    def test_init(self):
        assert self.pas.alert_count == 0

    def test_set_price_monitor(self):
        r = self.pas.set_price_monitor(
            item_type="flight",
            route="IST-LHR",
            target_price=200.0,
            current_price=300.0,
        )
        assert r["set"] is True
        assert r["gap_pct"] > 0
        assert self.pas.alert_count == 1

    def test_check_drop_alerts_triggered(self):
        r = self.pas.check_drop_alerts(
            current_price=80.0,
            previous_price=100.0,
            threshold_pct=10.0,
        )
        assert r["checked"] is True
        assert r["alert_triggered"] is True
        assert r["drop_pct"] == 20.0
        assert r["urgency"] == "high"

    def test_check_drop_alerts_not_triggered(self):
        r = self.pas.check_drop_alerts(
            current_price=95.0,
            previous_price=100.0,
        )
        assert r["alert_triggered"] is False
        assert r["urgency"] == "low"

    def test_compare_historical_all_time_low(self):
        r = self.pas.compare_historical(
            current_price=100.0,
            historical_prices=[150.0, 200.0, 180.0],
        )
        assert r["compared"] is True
        assert r["assessment"] == "all_time_low"

    def test_compare_historical_expensive(self):
        r = self.pas.compare_historical(
            current_price=300.0,
            historical_prices=[150.0, 160.0, 170.0],
        )
        assert r["assessment"] == "expensive"

    def test_compare_historical_no_data(self):
        r = self.pas.compare_historical(
            current_price=100.0
        )
        assert r["assessment"] == "no_data"

    def test_suggest_best_time_ideal(self):
        r = self.pas.suggest_best_time(
            months_ahead=4
        )
        assert r["suggested"] is True
        assert r["booking_advice"] == "ideal"
        assert r["expected_savings_pct"] == 25.0

    def test_suggest_best_time_late(self):
        r = self.pas.suggest_best_time(
            months_ahead=0
        )
        assert r["booking_advice"] == "late"

    def test_detect_deals(self):
        prices = [
            {"route": "A", "price": 100},
            {"route": "B", "price": 300},
            {"route": "C", "price": 280},
        ]
        r = self.pas.detect_deals(
            prices, threshold_pct=20.0
        )
        assert r["detected"] is True
        assert r["deal_count"] >= 1

    def test_detect_deals_empty(self):
        r = self.pas.detect_deals([])
        assert r["deal_count"] == 0


# ── TravelDocumentManager ─────────────────────


class TestTravelDocumentManager:
    """TravelDocumentManager testleri."""

    def setup_method(self):
        self.tdm = TravelDocumentManager()

    def test_init(self):
        assert self.tdm.document_count == 0

    def test_add_passport_valid(self):
        r = self.tdm.add_passport(
            holder_name="Fatih",
            passport_number="U12345",
            expiry_months=48,
        )
        assert r["added"] is True
        assert r["status"] == "valid"
        assert r["alert"] is False

    def test_add_passport_expiring(self):
        r = self.tdm.add_passport(
            expiry_months=4,
        )
        assert r["status"] == "expiring_soon"
        assert r["alert"] is True

    def test_add_passport_renew(self):
        r = self.tdm.add_passport(
            expiry_months=10,
        )
        assert r["status"] == "renew_recommended"

    def test_store_visa_valid(self):
        r = self.tdm.store_visa(
            country="US", visa_type="tourist",
            valid_months=12,
        )
        assert r["stored"] is True
        assert r["status"] == "valid"

    def test_store_visa_expired(self):
        r = self.tdm.store_visa(
            valid_months=0,
        )
        assert r["status"] == "expired"

    def test_store_visa_expiring(self):
        r = self.tdm.store_visa(
            valid_months=2,
        )
        assert r["status"] == "expiring_soon"

    def test_add_insurance(self):
        r = self.tdm.add_insurance(
            provider="Allianz",
            coverage_type="travel",
        )
        assert r["added"] is True
        assert r["provider"] == "Allianz"

    def test_add_booking_confirmation(self):
        r = self.tdm.add_booking_confirmation(
            booking_type="flight",
            reference="ABC123",
            provider="THY",
        )
        assert r["added"] is True
        assert r["reference"] == "ABC123"

    def test_check_expiry_alerts(self):
        self.tdm.add_passport(expiry_months=4)
        self.tdm.add_passport(expiry_months=48)
        r = self.tdm.check_expiry_alerts(
            threshold_months=6
        )
        assert r["checked"] is True
        assert r["expiring_count"] == 1
        assert r["valid_count"] == 1


# ── TravelExpenseTracker ───────────────────────


class TestTravelExpenseTracker:
    """TravelExpenseTracker testleri."""

    def setup_method(self):
        self.tet = TravelExpenseTracker()

    def test_init(self):
        assert self.tet.expense_count == 0

    def test_log_expense(self):
        r = self.tet.log_expense(
            category="food", amount=25.0,
            currency="EUR",
        )
        assert r["logged"] is True
        assert r["category"] == "food"
        assert self.tet.expense_count == 1

    def test_convert_currency_usd_try(self):
        r = self.tet.convert_currency(
            amount=100.0,
            from_currency="USD",
            to_currency="TRY",
        )
        assert r["converted"] is True
        assert r["converted_amount"] == 3200.0

    def test_convert_currency_eur_try(self):
        r = self.tet.convert_currency(
            amount=100.0,
            from_currency="EUR",
            to_currency="TRY",
        )
        assert r["converted_amount"] == 3500.0

    def test_track_budget_on_track(self):
        self.tet.log_expense(amount=300.0)
        self.tet.log_expense(amount=200.0)
        r = self.tet.track_budget(
            total_budget=1000.0
        )
        assert r["tracked"] is True
        assert r["status"] == "on_track"
        assert r["remaining"] == 500.0

    def test_track_budget_over(self):
        self.tet.log_expense(amount=800.0)
        self.tet.log_expense(amount=300.0)
        r = self.tet.track_budget(
            total_budget=1000.0
        )
        assert r["status"] == "over_budget"

    def test_track_budget_near_limit(self):
        self.tet.log_expense(amount=850.0)
        r = self.tet.track_budget(
            total_budget=1000.0
        )
        assert r["status"] == "near_limit"

    def test_manage_receipts(self):
        e = self.tet.log_expense(amount=50.0)
        r = self.tet.manage_receipts(
            expense_id=e["expense_id"],
            receipt_name="dinner.jpg",
        )
        assert r["managed"] is True
        assert r["total_receipts"] == 1

    def test_manage_receipts_not_found(self):
        r = self.tet.manage_receipts(
            expense_id="invalid"
        )
        assert r["managed"] is False

    def test_generate_report_empty(self):
        r = self.tet.generate_report()
        assert r["generated"] is True
        assert r["total"] == 0.0

    def test_generate_report(self):
        self.tet.log_expense(
            category="food", amount=100.0
        )
        self.tet.log_expense(
            category="food", amount=50.0
        )
        self.tet.log_expense(
            category="transport", amount=30.0
        )
        r = self.tet.generate_report()
        assert r["total"] == 180.0
        assert r["top_category"] == "food"
        assert r["expense_count"] == 3


# ── TravelOrchestrator ────────────────────────


class TestTravelOrchestrator:
    """TravelOrchestrator testleri."""

    def setup_method(self):
        self.to = TravelOrchestrator()

    def test_init(self):
        a = self.to.get_analytics()
        assert a["retrieved"] is True
        assert a["components"] == 8

    def test_plan_full_trip(self):
        r = self.to.plan_full_trip(
            origin="IST", destination="LHR",
            days=5, budget=3000.0,
        )
        assert r["planned"] is True
        assert "flights" in r
        assert "hotels" in r
        assert "visa" in r
        assert "itinerary" in r

    def test_travel_checklist(self):
        r = self.to.travel_checklist(
            passport_country="TR",
            destination="US",
        )
        assert r["generated"] is True
        assert r["item_count"] >= 3
        assert "passport_valid" in r["checklist"]

    def test_travel_checklist_visa_free(self):
        r = self.to.travel_checklist(
            passport_country="TR",
            destination="GE",
        )
        assert r["generated"] is True

    def test_get_analytics(self):
        r = self.to.get_analytics()
        assert r["flights_searched"] == 0
        assert r["hotels_searched"] == 0

    def test_analytics_after_trip(self):
        self.to.plan_full_trip(
            origin="IST", destination="CDG",
        )
        r = self.to.get_analytics()
        assert r["flights_searched"] >= 1
        assert r["itineraries_created"] >= 1
