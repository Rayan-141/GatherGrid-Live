import os
import datetime
import qrcode
import graphene
from models import UserObject, EventObject, BookingObject, PaymentObject, SeatObject, TicketObject
from db import get_driver


# ── Make qr_codes folder ─────────────────────────────────────────
os.makedirs("qr_codes", exist_ok=True)


# ── Helper: Get next ID ──────────────────────────────────────────
def get_next_id(label):
    with get_driver().session() as session:
        result = session.run(f"MATCH (n:{label}) RETURN COALESCE(MAX(n.id), 0) + 1 AS next_id")
        return result.single()["next_id"]


# ══════════════════════════════════════════════════════════════════
#  QUERIES
# ══════════════════════════════════════════════════════════════════
class Query(graphene.ObjectType):

    # ── Get event by ID ──
    event = graphene.Field(EventObject, id=graphene.Int(required=True))

    def resolve_event(self, info, id):
        print(f"🔍 DEBUG: Fetching event with ID: {id}", flush=True)
        with get_driver().session() as session:
            result = session.run("MATCH (e:Event {id: $id}) RETURN e", id=id)
            record = result.single()
            if record:
                e = record["e"]
                print(f"✅ DEBUG: Found Event node in DB: {dict(e)}", flush=True)
                return EventObject(
                    id=e.get("id"),
                    title=e.get("title"),
                    description=e.get("description", "No description available"),
                    venue=e.get("venue", "TBA"),
                    event_date=e.get("event_date", "TBA"),
                    total_seats=e.get("total_seats", 0),
                    price=e.get("price", 0.0)
                )
            print(f"❌ DEBUG: No Event found with ID: {id}", flush=True)
        return None

    # ── Get user by ID ──
    user = graphene.Field(UserObject, id=graphene.String(required=True))

    def resolve_user(self, info, id):
        with get_driver().session() as session:
            result = session.run("MATCH (u:User {id: $id}) RETURN u", id=str(id))
            record = result.single()
            if record:
                u = record["u"]
                return UserObject(id=u["id"], name=u["name"], email=u["email"], phone=u["phone"])
        return None

    # ── Get all events ──
    all_events = graphene.List(EventObject)

    def resolve_all_events(self, info):
        with get_driver().session() as session:
            result = session.run("MATCH (e:Event) RETURN e")
            events = []
            for record in result:
                e = record["e"]
                events.append(EventObject(
                    id=e.get("id"),
                    title=e.get("title"),
                    description=e.get("description", "No description available"),
                    venue=e.get("venue", "TBA"),
                    event_date=e.get("event_date", "TBA"),
                    total_seats=e.get("total_seats", 0),
                    price=e.get("price", 0.0)
                ))
            return events

    # ── Get all users ──
    all_users = graphene.List(UserObject)

    def resolve_all_users(self, info):
        with get_driver().session() as session:
            result = session.run("MATCH (u:User) RETURN u")
            users = []
            for record in result:
                u = record["u"]
                users.append(UserObject(id=u["id"], name=u["name"], email=u["email"], phone=u["phone"]))
            return users

    # ── Get booking by ID ──
    booking = graphene.Field(BookingObject, id=graphene.Int(required=True))

    def resolve_booking(self, info, id):
        with get_driver().session() as session:
            result = session.run("MATCH (b:Booking {id: $id}) RETURN b", id=id)
            record = result.single()
            if record:
                b = record["b"]
                return BookingObject(id=b["id"], booking_date=b["booking_date"],
                                     total_amount=b["total_amount"], status=b["status"])
        return None


# ══════════════════════════════════════════════════════════════════
#  MUTATION INPUTS
# ══════════════════════════════════════════════════════════════════
class CreateBookingInput(graphene.InputObjectType):
    user_name = graphene.String(required=True)
    user_email = graphene.String(required=True)
    user_phone = graphene.String(required=True)
    event_id = graphene.Int(required=True)
    event_title = graphene.String(required=True)
    event_venue = graphene.String(required=True)
    event_date = graphene.String(required=True)
    event_price = graphene.Float(required=True)
    event_image = graphene.String(required=True)
    seat_numbers = graphene.List(graphene.String, required=True)


# ══════════════════════════════════════════════════════════════════
#  MUTATIONS
# ══════════════════════════════════════════════════════════════════

# ── Create Booking ────────────────────────────────────────────────
class CreateBooking(graphene.Mutation):
    class Arguments:
        input = CreateBookingInput(required=True)

    booking = graphene.Field(BookingObject)

    def mutate(self, info, input):
        with get_driver().session() as session:

            # Step 1: Create or Find User
            session.run("""
                MERGE (u:User {email: $email})
                SET u.name = $name, u.phone = $phone, u.id = COALESCE(u.id, $email)
            """, email=input.user_email, name=input.user_name, phone=input.user_phone)
            print(f"👤 DEBUG: User {input.user_email} prepared.", flush=True)

            # Step 2: JIT Event & Seat Creation (MERGE)
            # This ensures only the booked event exists in the graph
            session.run("""
                MERGE (e:Event {id: $id})
                SET e.title = $title, e.venue = $venue, e.event_date = $event_date,
                    e.price = $price, e.image = $image, e.total_seats = 100
            """, id=input.event_id, title=input.event_title, venue=input.event_venue,
                 event_date=input.event_date, price=input.event_price, image=input.event_image)
            print(f"🏟️ DEBUG: Event '{input.event_title}' merged into graph.", flush=True)

            # Check and Create seats if missing
            for s_num in input.seat_numbers:
                # Generate a more unique numeric ID for the seat: (event_id * 1000) + (row_num * 10) + col_num
                # For simplicity, we just use a hash or a clean offset if possible.
                # Here we use seat_number suffix if it's like "1_3" -> 1*10 + 3 = 13.
                try:
                    row, col = s_num.split('_')
                    numeric_suffix = int(row) * 10 + int(col)
                except:
                    numeric_suffix = 999
                
                seat_node_id = (int(input.event_id) * 1000) + numeric_suffix

                session.run("""
                    MATCH (e:Event {id: $event_id})
                    MERGE (s:Seat {seat_number: $s_num, event_id: $event_id})
                    ON CREATE SET s.id = $id, s.status = 'available', s.price = $price
                    MERGE (e)-[:HAS_SEAT]->(s)
                """, event_id=int(input.event_id), s_num=s_num, 
                     id=seat_node_id, price=input.event_price)
                
                # Fetch status to verify
                result = session.run("""
                    MATCH (e:Event {id: $event_id})-[:HAS_SEAT]->(s:Seat {seat_number: $s_num})
                    RETURN s.status AS status
                """, event_id=int(input.event_id), s_num=s_num)
                record = result.single()
                if record["status"] != "available":
                    raise Exception(f"Seat {s_num} is already {record['status']}")
            
            event_title = input.event_title

            # Step 3: Calculate total amount
            result = session.run("""
                MATCH (e:Event {id: $event_id})-[:HAS_SEAT]->(s:Seat)
                WHERE s.seat_number IN $seat_numbers
                RETURN SUM(s.price) AS total
            """, event_id=int(input.event_id), seat_numbers=input.seat_numbers)
            total_amount = result.single()["total"]
            if total_amount is None:
                total_amount = input.event_price * len(input.seat_numbers)

            # Step 4: Create Booking node
            booking_id = get_next_id("Booking")
            booking_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            session.run("""
                MATCH (u:User {email: $email}), (e:Event {id: $event_id})
                CREATE (b:Booking {id: $booking_id, booking_date: $booking_date,
                                   total_amount: $total_amount, status: 'pending', 
                                   event_name: $event_name, seats_booked: $seats})
                CREATE (u)-[:MADE_BOOKING]->(b)
                CREATE (b)-[:FOR_EVENT]->(e)
            """, email=input.user_email, event_id=int(input.event_id),
                 booking_id=booking_id, booking_date=booking_date, 
                 total_amount=float(total_amount), event_name=event_title,
                 seats=", ".join(input.seat_numbers))
            print(f"📅 DEBUG: Booking {booking_id} created for Event {input.event_id}.", flush=True)

            # Step 5: Link seats + update status + create tickets
            for s_num in input.seat_numbers:
                # Update seat status to reserved
                session.run("""
                    MATCH (e:Event {id: $event_id})-[:HAS_SEAT]->(s:Seat {seat_number: $s_num})
                    SET s.status = 'reserved'
                """, event_id=int(input.event_id), s_num=s_num)

                # Fetch seat ID for ticket
                res = session.run("MATCH (e:Event {id: $event_id})-[:HAS_SEAT]->(s:Seat {seat_number: $s_num}) RETURN s.id AS sid", 
                                  event_id=int(input.event_id), s_num=s_num)
                seat_id = res.single()["sid"]

                # Link booking to seat
                session.run("""
                    MATCH (b:Booking {id: $booking_id}), (s:Seat {id: $seat_id})
                    CREATE (b)-[:INCLUDES_SEAT]->(s)
                """, booking_id=booking_id, seat_id=int(seat_id))

                # Generate QR code
                ticket_id = get_next_id("Ticket")
                qr_data = f"TICKET-{ticket_id}-BOOKING-{booking_id}-SEAT-{seat_id}"
                
                qr_dir = "qr_codes"
                import os
                os.makedirs(qr_dir, exist_ok=True)
                
                qr_path = f"{qr_dir}/ticket_{ticket_id}.png"

                qr = qrcode.make(qr_data)
                qr.save(qr_path)

                # Create Ticket node
                session.run("""
                    MATCH (b:Booking {id: $booking_id}), (s:Seat {id: $seat_id})
                    CREATE (t:Ticket {id: $ticket_id, qr_code: $qr_code})
                    CREATE (b)-[:HAS_TICKET]->(t)
                    CREATE (t)-[:FOR_SEAT]->(s)
                """, booking_id=booking_id, seat_id=seat_id,
                     ticket_id=ticket_id, qr_code=qr_path)
                print(f"🎟️ DEBUG: Ticket {ticket_id} created for Seat {seat_id}.", flush=True)

            return CreateBooking(booking=BookingObject(
                id=booking_id, booking_date=booking_date,
                total_amount=total_amount, status="pending",
                event_name=event_title,
                seats_booked=", ".join(input.seat_numbers)
            ))


# ── Confirm Payment ──────────────────────────────────────────────
class ConfirmPayment(graphene.Mutation):
    class Arguments:
        booking_id = graphene.Int(required=True)
        amount = graphene.Float(required=True)

    payment = graphene.Field(PaymentObject)

    def mutate(self, info, booking_id, amount):
        with get_driver().session() as session:

            # Check booking exists
            result = session.run("MATCH (b:Booking {id: $id}) RETURN b", id=booking_id)
            if not result.single():
                raise Exception(f"Booking {booking_id} not found")

            # Create Payment node
            payment_id = get_next_id("Payment")
            payment_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            session.run("""
                MATCH (b:Booking {id: $booking_id})
                CREATE (p:Payment {id: $payment_id, amount: $amount,
                                   payment_status: 'completed', payment_date: $payment_date})
                CREATE (b)-[:HAS_PAYMENT]->(p)
                SET b.status = 'confirmed'
            """, booking_id=booking_id, payment_id=payment_id,
                 amount=amount, payment_date=payment_date)
            print(f"💰 DEBUG: Payment {payment_id} confirmed for Booking {booking_id}.", flush=True)

            # Update all seats to 'booked'
            session.run("""
                MATCH (b:Booking {id: $booking_id})-[:INCLUDES_SEAT]->(s:Seat)
                SET s.status = 'booked'
            """, booking_id=booking_id)

            return ConfirmPayment(payment=PaymentObject(
                id=payment_id, amount=amount,
                payment_status="completed", payment_date=payment_date
            ))


# ── Cancel Booking ───────────────────────────────────────────────
class CancelBooking(graphene.Mutation):
    class Arguments:
        booking_id = graphene.Int(required=True)

    message = graphene.String()

    def mutate(self, info, booking_id):
        with get_driver().session() as session:

            # Check booking exists
            result = session.run("MATCH (b:Booking {id: $id}) RETURN b", id=booking_id)
            if not result.single():
                raise Exception(f"Booking {booking_id} not found")

            # Release seats back to available
            session.run("""
                MATCH (b:Booking {id: $booking_id})-[:INCLUDES_SEAT]->(s:Seat)
                SET s.status = 'available'
            """, booking_id=booking_id)

            # Delete tickets
            session.run("""
                MATCH (b:Booking {id: $booking_id})-[:HAS_TICKET]->(t:Ticket)
                DETACH DELETE t
            """, booking_id=booking_id)

            # Delete payment if exists
            session.run("""
                MATCH (b:Booking {id: $booking_id})-[:HAS_PAYMENT]->(p:Payment)
                DETACH DELETE p
            """, booking_id=booking_id)

            # Update booking status
            session.run("""
                MATCH (b:Booking {id: $booking_id})
                SET b.status = 'cancelled'
            """, booking_id=booking_id)

            return CancelBooking(message=f"Booking {booking_id} cancelled. Seats released.")


# ── Root Mutation ─────────────────────────────────────────────────
class Mutation(graphene.ObjectType):
    create_booking = CreateBooking.Field()
    confirm_payment = ConfirmPayment.Field()
    cancel_booking = CancelBooking.Field()


# ── Schema ────────────────────────────────────────────────────────
schema = graphene.Schema(query=Query, mutation=Mutation, auto_camelcase=False)
