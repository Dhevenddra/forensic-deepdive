import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Injectable({ providedIn: 'root' })
export class UserService {
  constructor(private http: HttpClient) {}

  getUser(id: string) {
    return this.http.get(`/api/users/${id}`);
  }

  listUsers() {
    return this.http.get('/api/users');
  }

  addUser(body: unknown) {
    return this.http.post('/api/users', body);
  }

  removeUser(id: string) {
    return this.http.delete(`/api/users/${id}`);
  }

  health() {
    return this.http.get('/health');
  }
}
