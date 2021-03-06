from datetime import datetime
import os
from typing import Text
from xmlrpc.client import Boolean
from flask_login import UserMixin
from sqlalchemy import ARRAY, BOOLEAN, Column, String, Integer
from flask_sqlalchemy import SQLAlchemy
from geoalchemy2.types import Geometry
from shapely.geometry import Point
from geoalchemy2.shape import to_shape
from geoalchemy2.elements import WKTElement
from geoalchemy2.functions import ST_DWithin
from geoalchemy2.types import Geography
from sqlalchemy.sql.expression import cast
from geoalchemy2.shape import from_shape
import hashlib

db = SQLAlchemy()

'''
setup_db(app):
    binds a flask application and a SQLAlchemy service
'''
def setup_db(app):
    database_path = os.getenv('DATABASE_URL', 'DATABASE_URL_WAS_NOT_SET?!')

    # https://stackoverflow.com/questions/62688256/sqlalchemy-exc-nosuchmoduleerror-cant-load-plugin-sqlalchemy-dialectspostgre
    database_path = database_path.replace('postgres://', 'postgresql://')

    app.config["SQLALCHEMY_DATABASE_URI"] = database_path
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.app = app
    db.init_app(app)

'''
    drops the database tables and starts fresh
    can be used to initialize a clean database
'''
def db_drop_and_create_all():
    db.drop_all()
    db.create_all()

    # Initial sample data:
    insert_sample_locations()

def insert_sample_locations():
    # We need to start with an user to be able to relate initial locations to them
    admin_user = User(
        full_name="Administrator",
        display_name="admin",
        email="admin@dummy.mail",
        password=hashlib.md5("admin".encode()).hexdigest()
    )
    admin_user.insert()
    
    loc1 = SampleLocation(
        geom=SampleLocation.point_representation(
            latitude=52.516247, 
            longitude=13.377711
        ),
        learner_or_mentor='Learner',
        language_learn = ['C++', 'C/C#','Python','Java', 'JavaScript'],
        language_speak = ['French', 'Spanish', 'English']
    )
    loc1.user = admin_user
    loc1.insert()

    loc2 = SampleLocation(
        geom=SampleLocation.point_representation(
            latitude=52.520608, 
            longitude=13.295581
        ),
        learner_or_mentor='Mentor'
    )
    loc2.user = admin_user
    loc2.insert()

    loc3 = SampleLocation(
        geom=SampleLocation.point_representation(
            latitude=52.473580, 
            longitude=13.405252
        ),
        learner_or_mentor='Learner'
    )
    loc3.user = admin_user
    loc3.insert()

    loc4 = SampleLocation(
        geom=SampleLocation.point_representation(
            latitude=52.5220, 
            longitude=13.4133
        ),
        learner_or_mentor='Mentor'
    )
    loc4.user = admin_user
    loc4.insert()

# ????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????
class SpatialConstants:
    SRID = 4326
class SampleLocation(db.Model): #first defined model class to store sample locations in the DB
    __tablename__ = 'sample_locations' #table is created and data is stored in a table   

    id = Column(Integer, primary_key=True) 
    #column in a table, primary key is an attribute that identifies the row of the respective table
    # description = Column(String(80)) #second column
    geom = Column(Geometry(geometry_type='POINT', srid=SpatialConstants.SRID))  
    learner_or_mentor = Column(String)
    user_name = Column(String)
    language_learn = Column(ARRAY(String))
    language_speak = Column(ARRAY(String))
    how_long_experienced = Column(String)
    how_long_learning = Column(String)
    online_inperson = Column(ARRAY(String))
    
    user_id = Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # user_name = Column(db.String, db.ForeignKey('users.display_name'))

    # userr = db.relationship('User', foreign_keys=[user_id])
    # user_namee = db.relationship('User', foreign_keys=[user_name])

    # many to one side of the relationship of SampleLocation with User
    user = db.relationship("User", back_populates="created_locations") 

    @staticmethod
    def point_representation(latitude, longitude):
        point = 'POINT(%s %s)' % (longitude, latitude)
        wkb_element = WKTElement(point, srid=SpatialConstants.SRID)
        return wkb_element

    @staticmethod
    def get_items_within_radius(lat, lng, radius):
        """Return all sample locations within a given radius (in meters)"""

        #TODO: The arbitrary limit = 100 is just a quick way to make sure 
        # we won't return tons of entries at once, 
        # paging needs to be in place for real usecase
        results = SampleLocation.query.filter(
            ST_DWithin(
                cast(SampleLocation.geom, Geography),
                cast(from_shape(Point(lng, lat)), Geography),
                radius)
            ).limit(100).all() 

        return [l.to_dict() for l in results]    

    def get_location_latitude(self):
        point = to_shape(self.geom)
        return point.y

    def get_location_longitude(self):
        point = to_shape(self.geom)
        return point.x  

    def to_dict(self):
        # user_name = User.display_name

        return {
            'id': self.id,
            # 'description': self.description,
            'location': {
                'lng': self.get_location_longitude(),
                'lat': self.get_location_latitude()
            },
            'learner_or_mentor' : self.learner_or_mentor,
            # 'address': self.address
            # 'user_name': User.display_name, 
            # 'user_name': User.query.get(id),
            'user_name': self.user_name,
            'language_learn': self.language_learn,
            'language_speak': self.language_speak,
            'how_long_experienced': self.how_long_experienced,
            'how_long_learning': self.how_long_learning,
            'online_inperson': self.online_inperson

        }    

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def update(self):
        db.session.commit()         

# User login page
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200), nullable=False) # i.e Hanna Barbera
    display_name = db.Column(db.String(20), unique=True, nullable=False) # i.e hanna_25
    email = db.Column(db.String(120), unique=True, nullable=False) # i.e hanna@hanna-barbera.com
    password = db.Column(db.String(32), nullable=False) 
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    created_locations = db.relationship('SampleLocation', back_populates='user', order_by="SampleLocation.geom", lazy=True) 

    created_cafe_locations = db.relationship('AddCafe', back_populates='user', order_by="AddCafe.geom", lazy=True) 

    
    
    @classmethod
    def get_by_id(cls, user_id):
        return cls.query.filter_by(id=user_id).first()
        
    def __repr__(self):
        return f"User({self.id}, '{self.display_name}', '{self.email}')"      

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def update(self):
        db.session.commit()  

class AddCafe(db.Model):
    __tablename__ = 'cafe_locations' 

    id = Column(Integer, primary_key=True) 
    geom = Column(Geometry(geometry_type='POINT', srid=SpatialConstants.SRID))  
    address_cafe = Column(String)
    wifi = Column(BOOLEAN)
    sockets = Column(BOOLEAN)
    work_friendly_table = Column(BOOLEAN)
    teracce = Column(BOOLEAN)
    pet_friendly = Column(BOOLEAN)
    quiet = Column(BOOLEAN)
    user_name = Column(String)
    
    user_id = Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship("User", back_populates="created_cafe_locations") 

    @staticmethod
    def point_representation(latitude, longitude):
        point = 'POINT(%s %s)' % (longitude, latitude)
        wkb_element = WKTElement(point, srid=SpatialConstants.SRID)
        return wkb_element

    @staticmethod
    def get_items_within_radius(lat, lng, radius):
        """Return all sample locations within a given radius (in meters)"""

        #TODO: The arbitrary limit = 100 is just a quick way to make sure 
        # we won't return tons of entries at once, 
        # paging needs to be in place for real usecase
        results = AddCafe.query.filter(
            ST_DWithin(
                cast(AddCafe.geom, Geography),
                cast(from_shape(Point(lng, lat)), Geography),
                radius)
            ).limit(100).all() 

        return [l.to_dict() for l in results]    

    def get_location_latitude(self):
        point = to_shape(self.geom)
        return point.y

    def get_location_longitude(self):
        point = to_shape(self.geom)
        return point.x  

    def to_dict(self):
        # user_name = User.display_name

        return {
            # 'description': self.description,
            'id': self.id,
            'address_cafe': self.address_cafe,
            'location': {
                'lng': self.get_location_longitude(),
                'lat': self.get_location_latitude()
            },
            'wifi' : self.wifi,
            'sockets': self.sockets,
            'work_friendly_table': self.work_friendly_table,
            'teracce': self.teracce,
            'pet_friendly': self.pet_friendly,
            'quiet': self.quiet,
            'user_name': self.user_name,
        }    

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def update(self):
        db.session.commit()         