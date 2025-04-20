import datetime
import json
from peewee import Model, SqliteDatabase, CharField, TextField, DateTimeField, AutoField, ForeignKeyField

# Initialize SQLite database
db = SqliteDatabase('paid_design.db')

class BaseModel(Model):
    class Meta:
        database = db

class DesignSession(BaseModel):
    """Represents a design session with a user."""
    session_id = CharField(primary_key=True)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)
    
    def save(self, *args, **kwargs):
        self.updated_at = datetime.datetime.now()
        return super(DesignSession, self).save(*args, **kwargs)

class DesignState(BaseModel):
    """Stores the current state of the design as a JSON object."""
    id = AutoField()
    session = ForeignKeyField(DesignSession, backref='states')
    state_json = TextField()  # JSON string containing the design state
    instructions = TextField(null=True)  # Voice agent instructions associated with this state
    created_at = DateTimeField(default=datetime.datetime.now)
    
    @property
    def state(self):
        """Returns the state as a Python dictionary."""
        return json.loads(self.state_json)
    
    @state.setter
    def state(self, value):
        """Sets the state from a Python dictionary."""
        self.state_json = json.dumps(value)

class Conversation(BaseModel):
    """Stores the conversation history for a design session."""
    id = AutoField()
    session = ForeignKeyField(DesignSession, backref='conversations')
    speaker = CharField()  # 'user' or 'agent'
    message = TextField()
    timestamp = DateTimeField(default=datetime.datetime.now)

def initialize_db():
    """Initialize the database and create tables if they don't exist."""
    # Check if the database is already connected
    if not db.is_closed():
        # Connection already open, just use it
        pass
    else:
        # Open a new connection
        db.connect()
    
    # Check if we need to add the instructions column to DesignState
    need_migration = False
    try:
        # Try to create tables first
        db.create_tables([DesignSession, DesignState, Conversation], safe=True)
        
        # Check if we need to add the instructions column
        columns = [column.name for column in db.get_columns('designstate')]
        if 'instructions' not in columns:
            need_migration = True
            print("Need to add instructions column to DesignState")
    except Exception as e:
        print(f"Database schema check error: {e}")
    
    # Perform migration if needed
    if need_migration:
        try:
            # Add the instructions column
            db.execute_sql('ALTER TABLE designstate ADD COLUMN instructions TEXT;')
            print("Added instructions column to DesignState")
        except Exception as e:
            print(f"Migration error: {e}")
    
    # Only close if we opened it
    if db.is_closed():
        pass
    else:
        db.close()