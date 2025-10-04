from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kanar_locations.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class KanarLocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    message = db.Column(db.String(200), nullable=False)
    car = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'lat': self.lat,
            'lon': self.lon,
            'message': self.message,
            'car': self.car,
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

        # Basic coordinate validation
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return jsonify({'error': 'Invalid coordinates'}), 400

        new_location = KanarLocation(lat=lat, lon=lon, message=message)
        db.session.add(new_location)
        db.session.commit()

        return jsonify(new_location.to_dict()), 201
    else:
        # Get timeout from query parameter, default to 15 minutes
        timeout_minutes = int(request.args.get('timeout', 15))
        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)

        # Delete expired locations
        KanarLocation.query.filter(KanarLocation.timestamp < cutoff_time).delete()
        db.session.commit()

        # Fetch remaining locations
        locations = KanarLocation.query.all()
        return jsonify([loc.to_dict() for loc in locations])

# Remove the update_location route as we no longer allow moving pins

@app.route('/create-database', methods=['GET'])
def create_database():
    try:
        init_db()  # Call the function to initialize the database
        return jsonify({'message': 'Database initialized successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/timeout', methods=['GET', 'POST'])
def admin_timeout():
    if request.method == 'POST':
        timeout = request.json.get('timeout')
        if not isinstance(timeout, int) or timeout < 0:
            return jsonify({'error': 'Invalid timeout value'}), 400

        # In a real application, you'd want to store this in a database
        # For simplicity, we'll use a file here
        with open('timeout.txt', 'w') as f:
            f.write(str(timeout))
        return jsonify({'message': 'Timeout updated successfully'}), 200
    else:
        try:
            with open('timeout.txt', 'r') as f:
                timeout = int(f.read().strip())
        except FileNotFoundError:
            timeout = 15  # Default to 15 minutes if file doesn't exist
        return jsonify({'timeout': timeout})

def init_db():
    with app.app_context():
        db.create_all()
        print("Database initialized.")

if __name__ == '__main__':
    init_db()  # Initialize the database before running the app
    app.run(debug=True, host='0.0.0.0', port=20778)