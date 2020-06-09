from kafka import KafkaConsumer
import config

def get_input():
    c = config.kafka_config
    consumer = KafkaConsumer(bootstrap_servers=[(('%s:%d') % (c['host'], c['port']))], consumer_timeout_ms=100)
    consumer.subscribe(c['topics'])

    return consumer


if __name__ == '__main__':
    """Test Kafka"""
    it = get_input()
    while True:
        for m in it:
            print(m)
