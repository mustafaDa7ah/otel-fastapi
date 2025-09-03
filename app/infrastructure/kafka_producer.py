import json
import logging
from confluent_kafka import Producer
from app.core.telemetry import get_logger_with_context, get_propagated_context

logger = get_logger_with_context(__name__)

class KafkaProducerService:
    def __init__(self, bootstrap_servers: str = 'kafka:9092'):
        self.conf = {
            'bootstrap.servers': bootstrap_servers,
            'client.id': 'fastapi-producer'
        }
        self.producer = Producer(self.conf)
        logger.info("Kafka producer initialized", extra={"attributes": {"bootstrap_servers": bootstrap_servers}})
    
    def produce_message(self, topic: str, key: str, value: dict):
        """Produce message with context propagation"""
        try:
            # Add context to the message
            message_with_context = value.copy()
            message_with_context['_context'] = get_propagated_context()
            
            # Produce to Kafka
            self.producer.produce(
                topic=topic,
                key=key,
                value=json.dumps(message_with_context),
                callback=self._delivery_callback
            )
            self.producer.poll(0)
            
            logger.info("Message produced to Kafka", extra={
                "attributes": {
                    "topic": topic,
                    "key": key,
                    "message_type": value.get('type', 'unknown')
                }
            })
            
        except Exception as e:
            logger.error("Failed to produce message to Kafka", extra={
                "attributes": {
                    "topic": topic,
                    "error": str(e)
                }
            })
            raise
    
    def _delivery_callback(self, err, msg):
        """Callback for message delivery"""
        if err:
            logger.error("Message delivery failed", extra={
                "attributes": {
                    "error": str(err),
                    "topic": msg.topic() if msg else 'unknown'
                }
            })
        else:
            logger.debug("Message delivered successfully", extra={
                "attributes": {
                    "topic": msg.topic(),
                    "partition": msg.partition(),
                    "offset": msg.offset()
                }
            })

# Singleton instance
kafka_producer = KafkaProducerService()