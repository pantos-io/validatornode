import sqlalchemy.orm


def modify_model_instance(model_instance, **modified_attributes):
    removed_attributes = [
        key for key, value in modified_attributes.items() if value is None
    ]
    updated_attributes = {
        key: value
        for key, value in modified_attributes.items() if value is not None
    }
    model_instance_dict = {
        key: value
        for key, value in model_instance.__dict__.items()
        if not isinstance(value, sqlalchemy.orm.state.InstanceState)
        and key not in removed_attributes
    }
    model_instance_dict.update(updated_attributes)
    return model_instance.__class__(**model_instance_dict)
