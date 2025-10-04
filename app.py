from flask import Flask, render_template, request, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import uuid
from flask import make_response

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///spot_locations.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret")
db = SQLAlchemy(app)

class SpotLocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    checkins = db.relationship('CheckinHistory', backref='location', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'lat': self.lat,
            'lon': self.lon,
            'name': self.name,
            'checkin_count': len(self.checkins),
            'checkin_history': [c.to_dict() for c in self.checkins],
            'timestamp': self.timestamp.isoformat()
        }

class CheckinHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey('spot_location.id'), nullable=False)
    user_id = db.Column(db.String(64), nullable=False)
    tags = db.Column(db.String(200), nullable=True)  # comma-separated tags
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'location_id': self.location_id,
            'user_id': self.user_id,
            'tags': self.tags.split(',') if self.tags else [],
            'timestamp': self.timestamp.isoformat()
        }


@app.route('/')
def index():
    resp = make_response(render_template('index.html'))
    if not request.cookies.get('user_id'):
        user_id = str(uuid.uuid4())  # random unique id
        resp.set_cookie('user_id', user_id, max_age=60*60*24*365)  # 1 year
    return resp

@app.route('/api/locations', methods=['GET', 'POST'])
def locations():
    if request.method == 'POST':
        data = request.json
        if not data:
            return jsonify({'error': 'Missing JSON data'}), 400

        lat = data.get('lat')
        lon = data.get('lon')
        name = data.get('name')

        if lat is None or lon is None or name is None:
            return jsonify({'error': 'Missing required fields'}), 400

        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return jsonify({'error': 'Invalid coordinates'}), 400

        new_location = SpotLocation(lat=lat, lon=lon, name=name)
        db.session.add(new_location)
        db.session.commit()

        return jsonify(new_location.to_dict()), 201
    else:
        timeout_minutes = int(request.args.get('timeout', 15))
        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)

        SpotLocation.query.filter(SpotLocation.timestamp < cutoff_time).delete()
        db.session.commit()

        locations = SpotLocation.query.all()
        return jsonify([loc.to_dict() for loc in locations])

@app.route('/api/locations/<int:location_id>/checkin', methods=['POST'])
def checkin_location(location_id):
    location = SpotLocation.query.get(location_id)
    if location is None:
        flash("Location not found", "error")
        return jsonify({'error': 'Location not found'}), 404

    user_id = request.cookies.get('user_id')
    if not user_id:
        flash("User not identified", "error")
        return jsonify({'error': 'User not identified'}), 400

    existing = CheckinHistory.query.filter_by(location_id=location.id, user_id=user_id).first()
    if existing:
        flash("You already checked in here", "error")
        return jsonify({'error': 'You already checked in this location'}), 400

    tags = request.json.get('tags', [])
    if not isinstance(tags, list) or not all(t in ['food', 'nature', 'sport', 'party', 'culture'] for t in tags):
        flash("Invalid tags", "error")
        return jsonify({'error': 'Invalid tags'}), 400

    checkin = CheckinHistory(location_id=location.id, user_id=user_id, tags=','.join(tags))
    db.session.add(checkin)
    db.session.commit()

    flash("Checkin recorded successfully!", "success")
    return jsonify({'message': 'Checkin recorded', 'location': location.to_dict()})



@app.route('/create-database', methods=['GET'])
def create_database():
    try:
        init_db()
        return jsonify({'message': 'Database initialized successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/timeout', methods=['GET', 'POST'])
def admin_timeout():
    if request.method == 'POST':
        timeout = request.json.get('timeout')
        if not isinstance(timeout, int) or timeout < 0:
            return jsonify({'error': 'Invalid timeout value'}), 400

        with open('timeout.txt', 'w') as f:
            f.write(str(timeout))
        return jsonify({'message': 'Timeout updated successfully'}), 200
    else:
        try:
            with open('timeout.txt', 'r') as f:
                timeout = int(f.read().strip())
        except FileNotFoundError:
            timeout = 15
        return jsonify({'timeout': timeout})

@app.route('/api/mock-data', methods=['POST'])
def load_mock_data():
    data = request.json
    if not data or "locations" not in data:
        return jsonify({"error": "Missing 'locations' key"}), 400

    created_locations = []
    for loc in data["locations"]:
        lat = loc.get("lat")
        lon = loc.get("lon")
        name = loc.get("name")
        checkins = loc.get("checkins", [])

        if lat is None or lon is None or name is None:
            continue  # skip invalid entries

        location = SpotLocation(lat=lat, lon=lon, name=name)
        db.session.add(location)
        db.session.flush()  # get location.id before commit

        for c in checkins:
            user_id = c.get("user_id", str(uuid.uuid4()))
            tags = ",".join(c.get("tags", []))
            checkin = CheckinHistory(location_id=location.id, user_id=user_id, tags=tags)
            db.session.add(checkin)

        created_locations.append(location.to_dict())

    db.session.commit()
    return jsonify({"message": "Mock data loaded", "locations": created_locations}), 201


def init_db():
    with app.app_context():
        db.create_all()
        print("Database initialized.")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=20778)
