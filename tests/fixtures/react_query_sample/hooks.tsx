import { useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';

export function useUser(id) {
  return useQuery({
    queryKey: ['user', id],
    queryFn: () => fetch(`/api/users/${id}`).then((r) => r.json()),
  });
}

export function useUserList() {
  return useQuery({
    queryKey: ['users'],
    queryFn: () => fetch('/api/users', { method: 'GET' }),
  });
}

export function useAddUser() {
  return useMutation({
    mutationFn: (body) => axios.post('/api/users', body),
  });
}

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => fetch('/health'),
  });
}
