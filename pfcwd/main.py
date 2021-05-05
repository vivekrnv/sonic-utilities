import importlib
import os
import sys

import click
import utilities_common.cli as clicommon
from natsort import natsorted
from sonic_py_common.multi_asic import get_external_ports
from tabulate import tabulate
from utilities_common import multi_asic as multi_asic_util
from utilities_common import constants
from sonic_py_common import logger

SYSLOG_IDENTIFIER = "config"

log = logger.Logger(SYSLOG_IDENTIFIER)

# mock the redis for unit test purposes #
try:
    if os.environ["UTILITIES_UNIT_TESTING"] == "2":
        modules_path = os.path.join(os.path.dirname(__file__), "..")
        tests_path = os.path.join(modules_path, "tests")
        sys.path.insert(0, modules_path)
        sys.path.insert(0, tests_path)
        import mock_tables.dbconnector
    if os.environ["UTILITIES_UNIT_TESTING_TOPOLOGY"] == "multi_asic":
        import mock_tables.mock_multi_asic
        importlib.reload(mock_tables.mock_multi_asic)
        mock_tables.dbconnector.load_namespace_config()

except KeyError:
    pass

# Default configuration
DEFAULT_DETECTION_TIME = 200
DEFAULT_RESTORATION_TIME = 200
DEFAULT_POLL_INTERVAL = 200
DEFAULT_PORT_NUM = 32
DEFAULT_ACTION = 'drop'

STATS_DESCRIPTION = [
    ('STORM DETECTED/RESTORED', 'PFC_WD_QUEUE_STATS_DEADLOCK_DETECTED', 'PFC_WD_QUEUE_STATS_DEADLOCK_RESTORED'),
    ('TX OK/DROP',              'PFC_WD_QUEUE_STATS_TX_PACKETS',        'PFC_WD_QUEUE_STATS_TX_DROPPED_PACKETS'),
    ('RX OK/DROP',              'PFC_WD_QUEUE_STATS_RX_PACKETS',        'PFC_WD_QUEUE_STATS_RX_DROPPED_PACKETS'),
    ('TX LAST OK/DROP',         'PFC_WD_QUEUE_STATS_TX_PACKETS_LAST',   'PFC_WD_QUEUE_STATS_TX_DROPPED_PACKETS_LAST'),
    ('RX LAST OK/DROP',         'PFC_WD_QUEUE_STATS_RX_PACKETS_LAST',   'PFC_WD_QUEUE_STATS_RX_DROPPED_PACKETS_LAST'),
]

CONFIG_DESCRIPTION = [
    ('ACTION',           'action',           'drop'),
    ('DETECTION TIME',   'detection_time',   'N/A'),
    ('RESTORATION TIME', 'restoration_time', 'infinite')
]

STATS_HEADER = ('QUEUE', 'STATUS',) + list(zip(*STATS_DESCRIPTION))[0]
CONFIG_HEADER = ('PORT',) + list(zip(*CONFIG_DESCRIPTION))[0]

CONFIG_DB_PFC_WD_TABLE_NAME = 'PFC_WD'
PORT_QOS_MAP =  "PORT_QOS_MAP"

# Main entrypoint
@click.group()
def cli():
    """ SONiC PFC Watchdog """


def get_all_queues(db, namespace=None, display=constants.DISPLAY_ALL):
    queue_names = db.get_all(db.COUNTERS_DB, 'COUNTERS_QUEUE_NAME_MAP')
    queues = list(queue_names.keys()) if queue_names else {}
    if display == constants.DISPLAY_ALL:
        return natsorted(queues)
    # filter the backend ports
    display_ports = [q.split(":")[0] for q in queues]
    display_ports = get_external_ports(display_ports, namespace)
    queues = [q for q in queues if q.split(":")[0] in display_ports]
    return natsorted(queues)


def get_all_ports(db, namespace=None, display=constants.DISPLAY_ALL):
    all_port_names = db.get_all(db.COUNTERS_DB, 'COUNTERS_PORT_NAME_MAP')

    # Get list of physical ports
    port_names = {}
    for i in all_port_names:
        if i.startswith('Ethernet'):
            port_names[i] = all_port_names[i]
    display_ports = list(port_names.keys())
    if display == constants.DISPLAY_EXTERNAL:
        display_ports = get_external_ports(display_ports, namespace)
    return natsorted(display_ports)


def get_server_facing_ports(db):
    candidates = db.get_table('DEVICE_NEIGHBOR')
    server_facing_ports = []
    for port in candidates:
        neighbor = db.get_entry(
            'DEVICE_NEIGHBOR_METADATA', candidates[port]['name']
        )
        if neighbor and neighbor['type'].lower() == 'server':
            server_facing_ports.append(port)
    if not server_facing_ports:
        server_facing_ports = [p[1] for p in db.get_table('VLAN_MEMBER')]
    return server_facing_ports


class PfcwdCli(object):
    def __init__(
        self, db=None, namespace=None, display=constants.DISPLAY_ALL
    ):
        self.db = None
        self.config_db = None
        self.multi_asic = multi_asic_util.MultiAsic(
            display, namespace, db
        )
        self.table = []
        self.all_ports = []

    @multi_asic_util.run_on_multi_asic
    def collect_stats(self, empty, queues):
        table = []

        if len(queues) == 0:
            queues = get_all_queues(
                self.db,
                self.multi_asic.current_namespace,
                self.multi_asic.display_option
            )

        for queue in queues:
            stats_list = []
            queue_oid = self.db.get(
                self.db.COUNTERS_DB, 'COUNTERS_QUEUE_NAME_MAP', queue
            )
            if queue_oid is None:
                continue
            stats = self.db.get_all(
                self.db.COUNTERS_DB, 'COUNTERS:' + queue_oid
            )
            if stats is None:
                continue
            for stat in STATS_DESCRIPTION:
                line = stats.get(stat[1], '0') + '/' + stats.get(stat[2], '0')
                stats_list.append(line)
            if stats_list != ['0/0'] * len(STATS_DESCRIPTION) or empty:
                table.append(
                    [queue, stats.get('PFC_WD_STATUS', 'N/A')] + stats_list
                )

        self.table += table

    def show_stats(self, empty, queues):
        del self.table[:]
        self.collect_stats(empty, queues)
        click.echo(tabulate(
            self.table, STATS_HEADER, stralign='right', numalign='right',
            tablefmt='simple'
        ))

    @multi_asic_util.run_on_multi_asic
    def get_all_namespace_ports(self):
        ports = get_all_ports(
            self.db, self.multi_asic.current_namespace,
            self.multi_asic.display_option
        )
        self.all_ports.extend(ports)

    def get_invalid_ports(self, ports=[]):
        if len(ports) == 0:
            return []
        self.get_all_namespace_ports()
        port_set = set(ports)
        # "all" is a valid option, remove before performing set diff
        port_set.discard("all")
        return port_set - set(self.all_ports)

    @multi_asic_util.run_on_multi_asic
    def collect_config(self, ports):
        table = []

        if len(ports) == 0:
            ports = get_all_ports(
                self.db, self.multi_asic.current_namespace,
                self.multi_asic.display_option
            )

        ports_found = False
        for port in ports:
            config_list = []
            config_entry = self.config_db.get_entry(
                CONFIG_DB_PFC_WD_TABLE_NAME, port
            )
            if config_entry is None or config_entry == {}:
                continue
            ports_found = True
            for config in CONFIG_DESCRIPTION:
                line = config_entry.get(config[1], config[2])
                config_list.append(line)
            table.append([port] + config_list)

        if not ports_found:
            return

        poll_interval = self.config_db.get_entry(
            CONFIG_DB_PFC_WD_TABLE_NAME, 'GLOBAL'
        ).get('POLL_INTERVAL')

        current_ns = self.multi_asic.current_namespace
        asic_namesapce = \
            "" if current_ns is None or current_ns == "" else " on {}".format(
                current_ns
            )
        if poll_interval is not None:
            click.echo(
                "Changed polling interval to {}ms{}".format(
                    poll_interval, asic_namesapce
                )
            )

        big_red_switch = self.config_db.get_entry(
            CONFIG_DB_PFC_WD_TABLE_NAME, 'GLOBAL'
        ).get('BIG_RED_SWITCH')

        if big_red_switch is not None:
            click.echo("BIG_RED_SWITCH status is {}{}".format(
                big_red_switch, asic_namesapce
            ))

        self.table += table

    def config(self, ports):
        del self.table[:]
        self.collect_config(ports)
        click.echo(tabulate(
            self.table, CONFIG_HEADER, stralign='right', numalign='right',
            tablefmt='simple'
        ))

    def start(self, action, restoration_time, ports, detection_time):
        invalid_ports = self.get_invalid_ports(ports)
        if len(invalid_ports):
            click.echo("Failed to run command, invalid options:")
            for opt in invalid_ports:
                click.echo(opt)
            exit()
        self.start_cmd(action, restoration_time, ports, detection_time)


    def verify_pfc_enable_status_per_port(self, port, pfcwd_info):
        pfc_status = self.config_db.get_entry(PORT_QOS_MAP, port).get('pfc_enable')
        if pfc_status is None:
            log.log_warning("SKIPPED: PFC is not enabled on port: {}".format(port), also_print_to_console=True)
            return

        self.config_db.mod_entry(
            CONFIG_DB_PFC_WD_TABLE_NAME, port, None
        )
        self.config_db.mod_entry(
            CONFIG_DB_PFC_WD_TABLE_NAME, port, pfcwd_info
        )

    @multi_asic_util.run_on_multi_asic
    def start_cmd(self, action, restoration_time, ports, detection_time):
        if os.geteuid() != 0:
            exit("Root privileges are required for this operation")

        all_ports = get_all_ports(
            self.db, self.multi_asic.current_namespace,
            self.multi_asic.display_option
        )

        if len(ports) == 0:
            ports = all_ports

        pfcwd_info = {
            'detection_time': detection_time,
        }
        if action is not None:
            pfcwd_info['action'] = action
        if restoration_time is not None:
            pfcwd_info['restoration_time'] = restoration_time
        else:
            pfcwd_info['restoration_time'] = 2 * detection_time
            click.echo(
                "restoration time not defined; default to 2 times "
                "detection time: {} ms".format(2 * detection_time)
            )

        for port in ports:
            if port == "all":
                for p in all_ports:
                    self.verify_pfc_enable_status_per_port(p, pfcwd_info)
            else:
                if port not in all_ports:
                    continue
                self.verify_pfc_enable_status_per_port(port, pfcwd_info)

    @multi_asic_util.run_on_multi_asic
    def interval(self, poll_interval):
        if os.geteuid() != 0:
            exit("Root privileges are required for this operation")
        pfcwd_info = {}
        if poll_interval is not None:
            pfcwd_table = self.config_db.get_table(CONFIG_DB_PFC_WD_TABLE_NAME)
            entry_min = 3000
            for entry in pfcwd_table:
                if("Ethernet" not in entry):
                    continue
                detection_time_entry_value = int(self.config_db.get_entry(
                    CONFIG_DB_PFC_WD_TABLE_NAME, entry
                ).get('detection_time'))
                restoration_time_entry_value = int(self.config_db.get_entry(
                    CONFIG_DB_PFC_WD_TABLE_NAME, entry
                ).get('restoration_time'))
                if ((detection_time_entry_value is not None) and
                    (detection_time_entry_value < entry_min)
                ):
                    entry_min = detection_time_entry_value
                    entry_min_str = "detection time"
                if ((restoration_time_entry_value is not None) and
                    (restoration_time_entry_value < entry_min)
                ):
                    entry_min = restoration_time_entry_value
                    entry_min_str = "restoration time"
            if entry_min < poll_interval:
                click.echo(
                   "unable to use polling interval = {}ms, value is "
                   "bigger than one of the configured {} values, "
                   "please choose a smaller polling_interval".format(
                        poll_interval, entry_min_str
                    ), err=True
                )
                exit(1)

            pfcwd_info['POLL_INTERVAL'] = poll_interval
            self.config_db.mod_entry(
                CONFIG_DB_PFC_WD_TABLE_NAME, "GLOBAL", pfcwd_info
            )

    @multi_asic_util.run_on_multi_asic
    def stop(self, ports):
        if os.geteuid() != 0:
            exit("Root privileges are required for this operation")

        all_ports = get_all_ports(
            self.db, self.multi_asic.current_namespace,
            self.multi_asic.display_option
        )

        if len(ports) == 0:
            ports = all_ports

        for port in ports:
            if port not in all_ports:
                continue
            self.config_db.mod_entry(CONFIG_DB_PFC_WD_TABLE_NAME, port, None)

    @multi_asic_util.run_on_multi_asic
    def start_default(self):
        if os.geteuid() != 0:
            exit("Root privileges are required for this operation")
        enable = self.config_db.get_entry('DEVICE_METADATA', 'localhost').get(
            'default_pfcwd_status'
        )

        # Get active ports from Config DB
        active_ports = natsorted(
            list(self.config_db.get_table('DEVICE_NEIGHBOR').keys())
        )

        if not enable or enable.lower() != "enable":
            return

        port_num = len(list(self.config_db.get_table('PORT').keys()))

        # Paramter values positively correlate to the number of ports.
        multiply = max(1, (port_num-1)//DEFAULT_PORT_NUM+1)
        pfcwd_info = {
            'detection_time': DEFAULT_DETECTION_TIME * multiply,
            'restoration_time': DEFAULT_RESTORATION_TIME * multiply,
            'action': DEFAULT_ACTION
        }

        for port in active_ports:
            self.verify_pfc_enable_status_per_port(port, pfcwd_info)

        pfcwd_info = {}
        pfcwd_info['POLL_INTERVAL'] = DEFAULT_POLL_INTERVAL * multiply
        self.config_db.mod_entry(
            CONFIG_DB_PFC_WD_TABLE_NAME, "GLOBAL", pfcwd_info
        )

    @multi_asic_util.run_on_multi_asic
    def counter_poll(self, counter_poll):
        if os.geteuid() != 0:
            exit("Root privileges are required for this operation")
        pfcwd_info = {}
        pfcwd_info['FLEX_COUNTER_STATUS'] = counter_poll
        self.config_db.mod_entry("FLEX_COUNTER_TABLE", "PFCWD", pfcwd_info)

    @multi_asic_util.run_on_multi_asic
    def big_red_switch(self, big_red_switch):
        if os.geteuid() != 0:
            exit("Root privileges are required for this operation")
        pfcwd_info = {}
        if big_red_switch is not None:
            pfcwd_info['BIG_RED_SWITCH'] = big_red_switch
        self.config_db.mod_entry(
            CONFIG_DB_PFC_WD_TABLE_NAME, "GLOBAL",
            pfcwd_info
        )


# Show stats
class Show(object):
    # Show commands
    @cli.group()
    def show():
        """ Show PFC Watchdog information"""

    @show.command()
    @multi_asic_util.multi_asic_click_options
    @click.option('-e', '--empty', is_flag=True)
    @click.argument('queues', nargs=-1)
    @clicommon.pass_db
    def stats(db, namespace, display, empty, queues):
        """ Show PFC Watchdog stats per queue """
        if (len(queues)):
            display = constants.DISPLAY_ALL
        PfcwdCli(db, namespace, display).show_stats(empty, queues)

    # Show config
    @show.command()
    @multi_asic_util.multi_asic_click_options
    @click.argument('ports', nargs=-1)
    @clicommon.pass_db
    def config(db, namespace, display, ports):
        """ Show PFC Watchdog configuration """
        PfcwdCli(db, namespace, display).config(ports)


# Start WD
class Start(object):
    @cli.command()
    @click.option(
        '--action', '-a', type=click.Choice(['drop', 'forward', 'alert'])
    )
    @click.option('--restoration-time', '-r', type=click.IntRange(100, 60000))
    @click.argument('ports', nargs=-1)
    @click.argument('detection-time', type=click.IntRange(100, 5000))
    @clicommon.pass_db
    def start(db, action, restoration_time, ports, detection_time):
        """
        Start PFC watchdog on port(s). To config all ports, use all as input.

        Example:

        sudo pfcwd start --action drop ports all detection-time 400 --restoration-time 400

        """
        PfcwdCli(db).start(
            action, restoration_time, ports, detection_time
        )


# Set WD poll interval
class Interval(object):
    @cli.command()
    @click.argument('poll_interval', type=click.IntRange(100, 3000))
    @clicommon.pass_db
    def interval(db, poll_interval):
        """ Set PFC watchdog counter polling interval """
        PfcwdCli(db).interval(poll_interval)


# Stop WD
class Stop(object):
    @cli.command()
    @click.argument('ports', nargs=-1)
    @clicommon.pass_db
    def stop(db, ports):
        """ Stop PFC watchdog on port(s) """
        PfcwdCli(db).stop(ports)


# Set WD default configuration on server facing ports when enable flag is on
class StartDefault(object):
    @cli.command("start_default")
    @clicommon.pass_db
    def start_default(db):
        """ Start PFC WD by default configurations  """
        PfcwdCli(db).start_default()


# Enable/disable PFC WD counter polling
class CounterPoll(object):
    @cli.command('counter_poll')
    @click.argument('counter_poll', type=click.Choice(['enable', 'disable']))
    @clicommon.pass_db
    def counter_poll(db, counter_poll):
        """ Enable/disable counter polling """
        PfcwdCli(db).counter_poll(counter_poll)


# Enable/disable PFC WD BIG_RED_SWITCH mode
class BigRedSwitch(object):
    @cli.command('big_red_switch')
    @click.argument('big_red_switch', type=click.Choice(['enable', 'disable']))
    @clicommon.pass_db
    def big_red_switch(db, big_red_switch):
        """ Enable/disable BIG_RED_SWITCH mode """
        PfcwdCli(db).big_red_switch(big_red_switch)


def get_pfcwd_clis():
    cli.add_command(BigRedSwitch().big_red_switch)
    cli.add_command(CounterPoll().counter_poll)
    cli.add_command(StartDefault().start_default)
    cli.add_command(Stop().stop)
    cli.add_command(Interval().interval)
    cli.add_command(Start().start)
    cli.add_command(Show().show)
    return cli


if __name__ == '__main__':
    cli = get_pfcwd_clis()
    cli()
