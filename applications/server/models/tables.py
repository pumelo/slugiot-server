#########################################################################
## Define your tables below, for example
##
## >>> db.define_table('mytable',Field('myfield','string'))
##
## Fields can be 'string','text','password','integer','double','boolean'
##       'date','time','datetime','blob','upload', 'reference TABLENAME'
## There is an implicit 'id integer autoincrement' field
## Consult manual for more options, validators, etc.
##
## More API examples for controllers:
##
## >>> db.mytable.insert(myfield='value')
## >>> rows=db(db.mytable.myfield=='value').select(db.mytable.ALL)
## >>> for row in rows: print row.id, row.myfield
#########################################################################

## after defining tables, uncomment below to enable auditing
# auth.enable_record_versioning(db)

import datetime
import uuid


#########################
# Server organization tables.

if auth.user is None:
    identifier = ''
else:
    identifier = auth.user.email

# Keeps track of devices.
db.define_table('device',
                # if we give the device an ID, we can do checks to verify devices belong to which device
                Field('device_id', 'string', writable=False, required=True, default=uuid.uuid4()),
                Field('user_email', 'string', writable=False, required=True, default=identifier),
                Field('name', 'string', required=True),  # Name of device
                Field('description', 'text')
                )

db.device.name.widget = lambda f, v: SQLFORM.widgets.string.widget(f, v, _placeholder='Enter the name of device')
db.device.description.widget = lambda f, v: SQLFORM.widgets.string.widget(f, v, _placeholder='Enter a description here')

# with this new split table definition it makes sense to just use the automatic id in this table as the procedure_id
db.define_table('procedures',
                Field('device_id', 'string', required=True),
                Field('name', 'string', required=True)  # Name of procedure used for file on client should be unique per device_id
                )

db.define_table('procedure_revisions',
                Field('procedure_id', 'bigint', required=True),  # key
                Field('procedure_data', 'text', required=True),  # Actual code for procedure - is check IS_LENGTH(65536) ok?
                # Otherwise use string and specifiy larger length
                Field('last_update', 'datetime', default=datetime.datetime.utcnow(), required=True),
                Field('is_stable', 'boolean', required=True)  # True for stable False for not stable
                )

db.device.id.readable = False

##############
# Permission table.

# Permission types.
# v = view
# a = admin (valid only for one whole device)
# e = edit settings of procedure
db.define_table('user_permission',
                Field('perm_user_email', required =True),
                # The email of the currently logged in user can be found in auth.user.email
                Field('device_id', required = True),
                Field('procedure_id'), # If this is Null, then permission is for whole device.
                # If None, then the permission is valid for ALL procedures.
                Field('perm_type',required = True) # 'e'=edit, 'v'=view, etc.
                # See above.
                )


#########################
# Settings are synched "down" to the client.

db.define_table('client_setting',
                Field('device_id'),
                Field('procedure_id'), # Can be Null for device-wide settings.
                Field('setting_name'),
                Field('setting_value'), # Encoded in json-plus.
                Field('last_updated', 'datetime', update=datetime.datetime.utcnow())
                )


#########################
## These tables are synched "up" from the clients to the server.

# Synched client -> server
db.define_table('logs',
                Field('device_id'),
                Field('procedure_id'), ## MOVE TO procedure_id
                Field('log_level', 'integer'), #  int, 0 = most important.
                Field('log_message', 'text'),
                Field('time_stamp', 'datetime'),
                Field('received_time_stamp', 'datetime', default=datetime.datetime.utcnow())
                )

# Synched client -> server
db.define_table('outputs',
                Field('device_id'),
                Field('procedure_id'),
                Field('name'), # Name of variable
                Field('output_value', 'text'), # Json, short please
                Field('tag'),
                Field('time_stamp', 'datetime'),
                Field('received_time_stamp', 'datetime', default=datetime.datetime.utcnow()),
)

## TODO: define the tables that need to be synched "down", for settings, and procedures.

############ Test tables.
## This is the table used to temporary testing editor
## it get procedure by the table id instead of device id
## because Team2 provide API for us to get the data from procedures
## we will delete this table at the final edition.
db.define_table('coding',
            Field('procedures', 'text'),
            Field('times','datetime')
            )

# Test table for inserting a procedure. Whatever gets inserted here is garbage.
db.define_table('procedures_trash',
                Field('device_id', 'string', required=True),
                Field('name', 'string', required=True)
                # Name of procedure used for file on client should be unique per device_id
                )