from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class UserStateManager:
    """Менеджер состояний пользователей с поддержкой навигации"""
    
    def __init__(self):
        self._states: Dict[int, Dict[str, Any]] = {}
    
    def get_state(self, user_id: int) -> Dict[str, Any]:
        """Получает состояние пользователя"""
        if user_id not in self._states:
            self._states[user_id] = {
                'data': {},
                'history': [],
                'current_step': None
            }
        return self._states[user_id]
    
    def set_data(self, user_id: int, key: str, value: Any):
        """Устанавливает данные пользователя"""
        state = self.get_state(user_id)
        state['data'][key] = value
    
    def get_data(self, user_id: int, key: str, default=None) -> Any:
        """Получает данные пользователя"""
        state = self.get_state(user_id)
        return state['data'].get(key, default)
    
    def get_all_data(self, user_id: int) -> Dict[str, Any]:
        """Получает все данные пользователя"""
        state = self.get_state(user_id)
        return state['data'].copy()
    
    def clear_data(self, user_id: int):
        """Очищает данные пользователя"""
        if user_id in self._states:
            self._states[user_id]['data'] = {}
            self._states[user_id]['history'] = []
            self._states[user_id]['current_step'] = None
    
    def push_step(self, user_id: int, step: str, context: Dict[str, Any] = None):
        """Добавляет шаг в историю"""
        state = self.get_state(user_id)
        state['history'].append({
            'step': step,
            'context': context or {}
        })
        state['current_step'] = step
    
    def pop_step(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает предыдущий шаг из истории"""
        state = self.get_state(user_id)
        if state['history']:
            state['history'].pop()
            if state['history']:
                state['current_step'] = state['history'][-1]['step']
                return state['history'][-1]
        state['current_step'] = None
        return None
    
    def get_last_step(self, user_id: int) -> Optional[str]:
        """Получает последний шаг"""
        state = self.get_state(user_id)
        return state['current_step']
    
    def get_previous_step(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает предыдущий шаг без удаления"""
        state = self.get_state(user_id)
        if len(state['history']) >= 2:
            return state['history'][-2]
        return None
    
    def clear_state(self, user_id: int):
        """Полностью очищает состояние пользователя"""
        if user_id in self._states:
            del self._states[user_id]
    
    def delete_message_ids(self, user_id: int, *message_ids):
        """Сохраняет ID сообщений для последующего удаления"""
        state = self.get_state(user_id)
        if 'messages' not in state:
            state['messages'] = []
        for msg_id in message_ids:
            if msg_id:
                state['messages'].append(msg_id)
    
    def get_messages(self, user_id: int) -> list:
        """Получает список сохраненных сообщений"""
        state = self.get_state(user_id)
        return state.get('messages', [])
    
    def clear_messages(self, user_id: int):
        """Очищает список сообщений"""
        state = self.get_state(user_id)
        state['messages'] = []

# Глобальный экземпляр менеджера состояний
state_manager = UserStateManager()
