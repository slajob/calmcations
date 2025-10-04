from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///spot_locations.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class SpotLocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    message = db.Column(db.String(200), nullable=False)
    car = db.Column(db.Integer)
    c = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    checkouts = db.relationship('CheckoutHistory', backref='location', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'lat': self.lat,
            'lon': self.lon,
            'message': self.message,
            'car': self.car,
            'checkout_count': len(self.checkouts),
            'checkout_history': [c.to_dict() for c in self.checkouts],
            'timestamp': self.timestamp.isoformat()
        }

class CheckoutHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey('spot_location.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'location_id': self.location_id,
            'timestamp': self.timestamp.isoformat()
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/locations', methods=['GET', 'POST'])
def locations():
    if request.method == 'POST':
        data = request.json
        if not data:
            return jsonify({'error': 'Missing JSON data'}), 400

        lat = data.get('lat')
        lon = data.get('lon')
        message = data.get('message')

        if lat is None or lon is None or message is None:
            return jsonify({'error': 'Missing required fields'}), 400

        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return jsonify({'error': 'Invalid coordinates'}), 400

        new_location = SpotLocation(lat=lat, lon=lon, message=message)
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

@app.route('/api/locations/<int:location_id>/checkout', methods=['POST'])
def checkout_location(location_id):
    location = SpotLocation.query.get(location_id)
    if location is None:
        return jsonify({'error': 'Location not found'}), 404

    # Add new checkout record
    checkout = CheckoutHistory(location_id=location.id)
    db.session.add(checkout)
    db.session.commit()

    return jsonify({
        'message': 'Checkout recorded',
        'location': location.to_dict()
    })

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

def init_db():
    with app.app_context():
        db.create_all()
        print("Database initialized.")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=20778)
