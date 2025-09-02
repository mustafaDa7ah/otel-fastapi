import logging
import requests
from uuid import UUID
from typing import List, Optional
from datetime import datetime
from opentelemetry import trace

from app.domain.models import User
from app.domain.repositories import UserRepository

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

class ClickHouseUserRepository(UserRepository):
    def __init__(self):
        self.base_url = "http://clickhouse:8123"
        self.database = "otel"
        self.auth = ('default', 'password')  # Authentication
        self._create_table()

    def _create_table(self):
        try:
            create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {self.database}.users (
                id UUID,
                name String,
                email String,
                created_at DateTime
            ) ENGINE = MergeTree()
            ORDER BY (created_at, id)
            """
            
            response = requests.post(
                f"{self.base_url}/",
                data=create_table_query,
                params={'database': self.database},
                auth=self.auth,  # ADD AUTH HERE
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info("ClickHouse users table created successfully")
            else:
                logger.error(f"Failed to create table: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Error creating table: {e}")

    def add(self, user: User) -> User:
        with tracer.start_as_current_span("clickhouse_repository_add") as span:
            span.set_attribute("user.id", str(user.id))
            span.set_attribute("user.name", user.name)
            
            try:
                insert_query = f"""
                INSERT INTO {self.database}.users (id, name, email, created_at) FORMAT Values
                """
                
                # Format datetime for ClickHouse (YYYY-MM-DD HH:MM:SS)
                clickhouse_datetime = user.created_at.strftime('%Y-%m-%d %H:%M:%S')
                escaped_name = user.name.replace("'", "''")
                escaped_email = user.email.replace("'", "''")
                values = f"('{user.id}', '{escaped_name}', '{escaped_email}', '{clickhouse_datetime}')"
                
                response = requests.post(
                    f"{self.base_url}/",
                    data=insert_query + values,
                    params={'database': self.database},
                    auth=self.auth,
                    timeout=5
                )
                
                if response.status_code == 200:
                    logger.info(f"ClickHouse: Added user {user.name} with ID {user.id}")
                    return user
                else:
                    logger.error(f"Failed to insert user: {response.status_code} - {response.text}")
                    raise Exception(f"ClickHouse insert failed: {response.text}")
                    
            except Exception as e:
                logger.error(f"Error inserting user into ClickHouse: {e}")
                return self._fallback_add(user)

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        with tracer.start_as_current_span("clickhouse_repository_get_by_id") as span:
            span.set_attribute("user.id", str(user_id))
            
            try:
                query = f"""
                SELECT id, name, email, created_at 
                FROM {self.database}.users 
                WHERE id = '{user_id}'
                FORMAT JSONCompact
                """
                
                response = requests.get(
                    f"{self.base_url}/",
                    params={
                        'database': self.database,
                        'query': query
                    },
                    auth=self.auth,  # ADD AUTH HERE
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data['data']:
                        user_data = data['data'][0]
                        logger.info(f"ClickHouse: Found user with ID {user_id}")
                        return User(
                            id=UUID(user_data[0]),
                            name=user_data[1],
                            email=user_data[2],
                            created_at=datetime.strptime(user_data[3], '%Y-%m-%d %H:%M:%S')  # Fix this line
                        )
                
                logger.warning(f"ClickHouse: User not found with ID {user_id}")
                return None
                
            except Exception as e:
                logger.error(f"Error fetching user from ClickHouse: {e}")
                return self._fallback_get_by_id(user_id)

    def get_all(self) -> List[User]:
        with tracer.start_as_current_span("clickhouse_repository_get_all"):
            try:
                query = f"""
                SELECT id, name, email, created_at 
                FROM {self.database}.users 
                ORDER BY created_at DESC
                FORMAT JSONCompact
                """
                
                response = requests.get(
                    f"{self.base_url}/",
                    params={
                        'database': self.database,
                        'query': query
                    },
                    auth=self.auth,
                    timeout=5
                )
                
                users = []
                if response.status_code == 200:
                    data = response.json()
                    for user_data in data['data']:
                        # ClickHouse returns datetime as 'YYYY-MM-DD HH:MM:SS'
                        users.append(User(
                            id=UUID(user_data[0]),
                            name=user_data[1],
                            email=user_data[2],
                            created_at=datetime.strptime(user_data[3], '%Y-%m-%d %H:%M:%S')
                        ))
                
                logger.info(f"ClickHouse: Returning {len(users)} users")
                return users
                
            except Exception as e:
                logger.error(f"Error fetching users from ClickHouse: {e}")
                return self._fallback_get_all()

    # Fallback methods
    def _fallback_add(self, user: User) -> User:
        if not hasattr(self, '_fallback_storage'):
            self._fallback_storage = []
        self._fallback_storage.append(user)
        logger.warning(f"Using fallback storage for user {user.id}")
        return user

    def _fallback_get_by_id(self, user_id: UUID) -> Optional[User]:
        if hasattr(self, '_fallback_storage'):
            for user in self._fallback_storage:
                if user.id == user_id:
                    return user
        return None

    def _fallback_get_all(self) -> List[User]:
        return getattr(self, '_fallback_storage', []).copy()