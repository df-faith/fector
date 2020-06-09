import input_kafka

def get_default_it():
    return input_kafka.get_input()

kafka_config = {'host' : 'kafka-host.org',
                'port': 1337,
                'topics': ['topic1',
                         'topic2',
                         'topic3',
                         'topic4']
                }

events_file = 'events.json'

default_n = 40

default_time = 5

ssh_gateway = ('localhost', 4242)

event_scripts = './events/'

parser_files = {'topic1' : 'format_syslog.json'}

rec_dir = './rec/'
fp_dir = './fp/'
cfp_dir = './cfp/'

match_dir = './match/'
matching_threshold = 0.8
matching_files = "cfp*.json"
