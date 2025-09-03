#!/usr/bin/env python3
import logging
import time
from app.infrastructure.kafka_consumer import kafka_consumer
from app.core.telemetry import get_logger_with_context

logger = get_logger_with_context(__name__)

def main():
    logger.info("Starting Kafka consumer service")
    
    # Wait a bit for Kafka to be fully ready
    time.sleep(10)
    
    try:
        # Subscribe to topics
        kafka_consumer.subscribe(['pipelines', 'test-topic'])
        
        # Start consuming
        kafka_consumer.start_consuming()
        
    except Exception as e:
        logger.error("Consumer failed to start", extra={"attributes": {"error": str(e)}})
        raise
    finally:
        kafka_consumer.stop()

if __name__ == "__main__":
    main()