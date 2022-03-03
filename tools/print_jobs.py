from rucio.db.sqla import session,models
print([request.to_dict()["state"] for request in session.get_session().query(models.Request).all()])
