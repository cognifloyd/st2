from st2common import log as logging
from st2common.exceptions.sensors import TriggerTypeRegistrationException
from st2common.persistence.reactor import TriggerType, TriggerInstance
from st2common.models.db.reactor import TriggerTypeDB, TriggerInstanceDB
from st2common.services import triggers as TriggerService
from st2common.util import reference

LOG = logging.getLogger('st2reactor.sensor.container_utils')


def create_trigger_instance(trigger, payload, occurrence_time):
    trigger_db = TriggerService.get_trigger_db(trigger)
    if trigger_db is None:
        LOG.info('No trigger in db for %s', trigger)
        return None
    trigger_instance = TriggerInstanceDB()
    trigger_instance.trigger = reference.get_ref_from_model(trigger_db)
    trigger_instance.payload = payload
    trigger_instance.occurrence_time = occurrence_time
    return TriggerInstance.add_or_update(trigger_instance)


def _create_trigger_type(content_pack, name, description=None, payload_schema=None,
                         parameters_schema=None):
    triggertypes = TriggerType.query(content_pack=content_pack, name=name)
    is_update = False
    if len(triggertypes) > 0:
        trigger_type = triggertypes[0]
        LOG.debug('Found existing trigger id:%s with name:%s. Will update '
                  'trigger.', trigger_type.id, name)
        is_update = True
    else:
        trigger_type = TriggerTypeDB()

    trigger_type.content_pack = content_pack
    trigger_type.name = name
    trigger_type.description = description
    trigger_type.payload_schema = payload_schema
    trigger_type.parameters_schema = parameters_schema
    try:
        triggertype_db = TriggerType.add_or_update(trigger_type)
    except:
        LOG.exception('Validation failed for TriggerType=%s.', trigger_type)
        raise TriggerTypeRegistrationException('Invalid TriggerType name=%s.' % name)
    if is_update:
        LOG.audit('TriggerType updated. TriggerType=%s', triggertype_db)
    else:
        LOG.audit('TriggerType created. TriggerType=%s', triggertype_db)
    return triggertype_db


def _validate_trigger_type(trigger_type):
    """
    XXX: We need validator objects that define the required and optional fields.
    For now, manually check them.
    """
    required_fields = ['name']
    for field in required_fields:
        if field not in trigger_type:
            raise TriggerTypeRegistrationException('Invalid trigger type. Missing field %s' % field)


def _create_trigger(trigger_type):
    if hasattr(trigger_type, 'parameters_schema') and not trigger_type['parameters_schema']:
        trigger_db = TriggerService.get_trigger_db(trigger_type.name)
        if trigger_db is None:
            trigger_dict = {'name': trigger_type.name, 'type': trigger_type.name}
            try:
                trigger_db = TriggerService.create_trigger_db(trigger_dict)
            except:
                LOG.exception('Validation failed for Trigger=%s.', trigger_dict)
                raise TriggerTypeRegistrationException(
                    'Unable to create Trigger for TriggerType=%s.' % trigger_type.name)
            else:
                return trigger_db
    else:
        LOG.debug('Won\'t create Trigger object as TriggerType %s expects ' +
                  'parameters.', trigger_type)
        return None


def _add_trigger_models(content_pack, trigger_type):
    description = trigger_type['description'] if 'description' in trigger_type else ''
    payload_schema = trigger_type['payload_schema'] if 'payload_schema' in trigger_type else {}
    parameters_schema = trigger_type['parameters_schema'] \
        if 'parameters_schema' in trigger_type else {}

    trigger_type = _create_trigger_type(
        content_pack=content_pack,
        name=trigger_type['name'],
        description=description,
        payload_schema=payload_schema,
        parameters_schema=parameters_schema
    )
    trigger = _create_trigger(trigger_type)
    return (trigger_type, trigger)


def add_trigger_models(content_pack, trigger_types):
    """
    Register trigger types.

    :param content_pack: Content pack those triggers belong to.
    :type content_pack: ``str``

    :param trigger_types: A list of triggers to register.
    :type trigger_types: ``list`` of ``dict``
    """
    [r for r in (_validate_trigger_type(trigger_type)
     for trigger_type in trigger_types) if r is not None]

    result = []
    for trigger_type in trigger_types:
        item = _add_trigger_models(content_pack=content_pack,
                                   trigger_type=trigger_type)

        if item:
            result.append(item)

    return result
