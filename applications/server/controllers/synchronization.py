# -*- coding: utf-8 -*-

import json_plus
import slugiot_synchronization

"""
 This method is to recieve log data.  It accepts two HTTP methods:
     GET: returns the latest log entries.  The 'limit' parameter limits
        number of results returned
     POST: accepts a JSON document with the output entries to ingest.  an
         example document is described below:
:return: Responds with a JSON object of saved settings from the server when a user posts using this function ands gets validated updated output_values from the server
:rtype: JSON object
 """
@request.restful()
def receive_logs():
    def GET(*args, **vars):
        limit = 3
        if ('limit' in request.vars):
            limit = int(request.vars.limit)
        logs = db(db.logs).select(orderby="received_time_stamp DESC",limitby=(0,limit))
        return response.json(logs)
    def POST(*args, **vars):
        request_body = request.body.read()
        try:
            saved_data = slugiot_synchronization.receive_append_data(request_body, 'logs')
            return response.json({"success":True,"table":"logs","insert_count":len(saved_data)})
        except Exception as e:
            raise HTTP(400, "there was an error saving log data: " + e.message)

    return locals()


"""
 This method is to recieve output data.  It accepts two HTTP methods:
     GET: returns the latest output entries.  planning on adding
         filtering based on device_id
     POST: accepts a JSON document with the output entries to ingest.  an
         example document is described below:
         {
             "device_id":"my_device",
             "output":
                 [
                     {"modulename":"my_module","name":"variable","output_value":"10","tag":"example","time_stamp":"2016-03-19 20:48:41"}
                 ]
         }
:return: Responds with a JSON object of saved settings from the server when a user posts using this function ands gets validated updated output_values from the server
:rtype: JSON object
 """
@request.restful()
def receive_outputs():
    def GET(*args, **vars):
        limit = 3
        if ('limit' in request.vars):
            limit = int(request.vars.limit)
        logs = db(db.outputs).select(orderby="received_time_stamp DESC", limitby=(0, limit))
        return response.json(logs)

    def POST(*args, **vars):
        request_body = request.body.read()
        try:
            saved_data = slugiot_synchronization.receive_append_data(request_body, 'outputs')
            return response.json({"success":True,"table":"outputs","insert_count":len(saved_data)})
        except Exception as e:
            raise HTTP(400, "there was an error saving log data: " + e.message)

    return locals()

"""
    This method is to receive value data.  It accepts two HTTP methods:
        GET: returns all the current output entries (for the device id)
        POST: accepts a JSON document with the value entries to ingest.
            all current entries (for the device_id) will be removed and replaced
            with the ones submitted.
            an example document is described below:
            {
                "device_id":"my_device",
                "module_values":
                    [
                        {"procedure_id":"proc1","name":"some_name","output_value":"some_value","time_stamp":"2016-04-19 01:04:25"},
                        {"procedure_id":"proc2","name":"some_other_name","output_value":"some_other_value"}
                    ]
            }
    :return: Responds with a JSON object of saved settings from the server when a user posts using this function ands gets validated updated module_values from the server
    :rtype: JSON object
"""

@request.restful()
def receive_module_values():
    def GET(*args, **vars):
        if (vars == None or not vars.has_key('device_id')):
            raise HTTP(400, "Please specify 'device_id' as a parameter to retrieve values")
        device_id = vars['device_id']
        vars = db(db.module_values.device_id == device_id).select()
        return response.json(vars)

    def POST(*args, **vars):
        # get the log data from the request and validate
        request_body = request.body.read()
        values_data = __get_validated_data(request_body, 'module_values')

        # get information from document
        device_id = values_data.get('device_id')
        values = values_data.get('module_values')

        for value in values:
            if (not isinstance(value, dict)):
                raise HTTP(400, "all module_values entries must be of type 'dict'")
            value["device_id"] = device_id
            if (value.get('id')):
                del value['id']

        try:
            # we may want to delete these in some cases
            # db(db.module_values.device_id == device_id).delete()
            db.module_values.bulk_insert(values)
        except Exception as e:
            db.rollback()
            raise HTTP(400, "there was an error saving value data: " + e.message)

        return response.json({"saved_values": values})

    return locals()


"""
    This method is to give setting data to the device.  Given a device_id, it returns
        all the setting information that the client needs.  If the parameter last_updated is set
        it will return only settings changed since that time

        GET: returns all the setting data as described above
        POST: a mechanism to actually set settings.  This is intended to be used for debugging
            {
              "device_id":"trevor",
              "settings":[
                    {"procedure_id":"proc1","setting_name":"some_setting","setting_value":"42"},
                    {"setting_name":"some_global_setting","setting_value":True}
              ]
            }
    :return: Responds with a JSON object of saved settings from the server when a user posts using this function ands gets validated updated module_values from the server
    :rtype: JSON object
"""
@request.restful()
def get_settings():
    def GET(*args, **vars):
        if (vars == None or not vars.has_key('device_id')):
            raise HTTP(400, "Please specify 'device_id' as a parameter to retrieve settings")
        device_id = vars['device_id']
        last_updated = datetime.datetime.fromtimestamp(1)
        if (vars.has_key('last_updated')):
            last_updated = vars['last_updated']

        settings = db((db.client_setting.device_id == device_id) & (db.client_setting.last_updated > last_updated)).select()
        return response.json(settings)

    def POST(*args, **vars):
        # get the log data from the request and validate
        request_body = request.body.read()
        values_data = __get_validated_data(request_body, 'settings')

        # get information from document
        device_id = values_data.get('device_id')
        settings = values_data.get('settings')

        for setting in settings:
            if (not isinstance(setting, dict)):
                raise HTTP(400, "all setting entries must be of type 'dict'")
            setting["device_id"] = device_id
            if (setting.get('id')):
                del setting['id']

        try:
            if (vars.has_key('delete_existing_settings') and vars['delete_existing_settings'] == "true"):
                db(db.client_setting.device_id == device_id).delete()
            for setting in settings:
                setting_name = setting['setting_name']
                setting_value = setting['setting_value']
                procedure_id = None
                if (setting.has_key('procedure_id')):
                    procedure_id = setting['procedure_id']
                db.client_setting.update_or_insert(
                    ((db.client_setting.setting_name == setting_name) & (db.client_setting.procedure_id == procedure_id) & (db.client_setting.device_id == device_id)),
                    setting_name=setting_name, setting_value=setting_value, procedure_id=procedure_id, device_id=device_id)

        except Exception as e:
            db.rollback()
            raise HTTP(400, "there was an error saving setting data: " + e.message)

        return response.json({"saved_settings": settings})

    return locals()

"""
This function takes in the data and ensures that it has the right format along with a device id  - {{"James",9001},{"Jo",3474},{"Jack",323}}

   :param p1: request_body for the data to be formatted properly
   :type p1: str
   :param p1: data_key
   :type p1: str
   :return: Data in a dictionary containing json-formatted data that has a device_id
   :rtype: Dictionary
"""
def __get_validated_data(request_body, data_key):
    if (not request_body):
        raise HTTP(400, "no data was included")
    try:
        data = json_plus.Serializable.loads(request_body)
    except:
        raise HTTP(400, "data was not json-formatted")
    if (not isinstance(data, dict)):
        raise HTTP(400, "data was not properly formatted")
    if (not data_key in data or not isinstance(data.get(data_key), list)):
        raise HTTP(400, "data needs to have list of data entries as '" + data_key + "'")
    if (not "device_id" in data and not isinstance(data.get('device_id'), str)):
        raise HTTP(400, "data needs to have string device id as 'device_id'")

    return data









