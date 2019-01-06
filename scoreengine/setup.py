from scoreengine import config, db_engine, models, utils


def init_from_config():
    """Initialize the database with teams (including a check team) and services."""
    with utils.session_scope() as session:
        models.Base.metadata.drop_all(db_engine)
        models.Base.metadata.create_all(db_engine)

        teams = {}
        assert config['teams']['minimum'] < config['teams']['maximum']
        for i in range(config['teams']['minimum'], config['teams']['maximum'] + 1):
            is_check_team = i == config['teams']['maximum']
            teams[i] = models.Team('Team {}'.format(i), check_team=is_check_team)
            session.add(teams[i])

        for cfg in config['services']:
            check_group, check_function = cfg['check'].split('.', 1)
            service = models.Service(cfg['name'], check_group, check_function)
            session.add(service)

            session.add_all(
                models.TeamService(
                    team,
                    service,
                    datum['key'],
                    str(datum['value']).format(team=team_num),
                    datum.get('edit'),
                    datum.get('hidden'),
                    order,
                )
                for team_num, team in teams.items()
                for order, datum in enumerate(cfg['data'])
            )
