from oslo_config import cfg


api_group = cfg.OptGroup(
    'api',
    title='API options',
    help='Options under this group are used to define staffeln API.'
)


test_opts = [
    cfg.StrOpt(
        'api_test_option',
        default='test',
        deprecated_group='DEFAULT',
        help='test options'
    ),
]

API_OPTS = (test_opts)


def register_opts(conf):
    conf.register_group(api_group)
    conf.register_opts(API_OPTS, group=api_group)


def list_opts():
    return {api_group: API_OPTS}
