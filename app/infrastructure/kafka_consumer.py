import json
import logging
from confluent_kafka import Consumer, KafkaError
from app.core.telemetry import get_logger_with_context, set_propagated_context

logger = get_logger_with_context(__name__)

class KafkaConsumerService:
    def __init__(self, bootstrap_servers: str = 'kafka:9092', group_id: str = 'fastapi-consumer-group'):
        self.conf = {
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': 'earliest'
        }
        self.consumer = Consumer(self.conf)
        self.running = False
        logger.info("Kafka consumer initialized", extra={"attributes": {
            "bootstrap_servers": bootstrap_servers,
            "group_id": group_id
        }})
    
    def subscribe(self, topics: list):
        """Subscribe to topics"""
        self.consumer.subscribe(topics)
        logger.info("Subscribed to topics", extra={"attributes": {"topics": topics}})
    
    def start_consuming(self):
        """Start consuming messages"""
        self.running = True
        logger.info("Starting Kafka consumer")
        
        try:
            while self.running:
                msg = self.consumer.poll(1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error("Kafka consumer error", extra={
                            "attributes": {"error": msg.error().str()}
                        })
                        continue
                
                # Process the message
                try:
                    self._process_message(msg)
                except Exception as e:
                    logger.error("Failed to process message", extra={
                        "attributes": {
                            "topic": msg.topic(),
                            "error": str(e)
                        }
                    })
                
        except KeyboardInterrupt:
            logger.info("Consumer stopped by user")
        finally:
            self.consumer.close()
    
    def _process_message(self, msg):
        """Process a single message with context propagation"""
        try:
            # Parse message
            message_data = json.loads(msg.value().decode('utf-8'))
            
            # Extract context if available
            context = message_data.pop('_context', {})
            
            # Set the propagated context
            set_propagated_context(context)
            
            # Log message receipt
            logger.info("Message received from Kafka", extra={
                "attributes": {
                    "topic": msg.topic(),
                    "partition": msg.partition(),
                    "offset": msg.offset(),
                    "key": msg.key().decode('utf-8') if msg.key() else None,
                    "message_type": message_data.get('type', 'unknown')
                }
            })
            
            # Process based on message type
            if message_data.get('type') == 'pipeline_create':
                self._process_pipeline(message_data)
            elif message_data.get('type') == 'user_message':
                self._process_user_message(message_data)
            else:
                logger.warning("Unknown message type", extra={
                    "attributes": {"message_data": message_data}
                })
                
        except Exception as e:
            logger.error("Failed to process message", extra={
                "attributes": {
                    "topic": msg.topic(),
                    "error": str(e)
                }
            })
    
    def _process_pipeline(self, message_data):
        """Process pipeline creation message"""
        from opentelemetry import trace
        tracer = trace.get_tracer(__name__)
        
        with tracer.start_as_current_span("pipeline.process.async"):
            pipeline_id = message_data['pipeline_id']
            steps = message_data['steps']
            
            logger.info("Processing async pipeline", extra={
                "attributes": {
                    "pipeline_id": pipeline_id,
                    "steps": steps,
                    "source": "kafka"
                }
            })
            
            # Simulate pipeline processing (similar to your sync version)
            for step in range(1, steps + 1):
                # Simulate work
                import time
                time.sleep(0.5)
                
                logger.info("Async pipeline step completed", extra={
                    "attributes": {
                        "pipeline_id": pipeline_id,
                        "step": step,
                        "total_steps": steps
                    }
                })
            
            logger.info("Async pipeline completed", extra={
                "attributes": {"pipeline_id": pipeline_id}
            })
    
    def _process_user_message(self, message_data):
        """Process user message"""
        logger.info("Processing user message", extra={
            "attributes": {
                "content": message_data.get('content', ''),
                "sender": message_data.get('sender', 'unknown')
            }
        })
    
    def stop(self):
        """Stop the consumer"""
        self.running = False
        logger.info("Stopping Kafka consumer")

# Singleton instance
kafka_consumer = KafkaConsumerService()