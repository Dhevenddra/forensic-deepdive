import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

export const usersApi = createApi({
  reducerPath: 'usersApi',
  baseQuery: fetchBaseQuery({ baseUrl: '/api' }),
  endpoints: (builder) => ({
    getUser: builder.query({
      query: (id) => `/api/users/${id}`,
    }),
    listUsers: builder.query({
      query: () => ({ url: '/api/users', method: 'GET' }),
    }),
    addUser: builder.mutation({
      query: (body) => ({ url: '/api/users', method: 'POST', body }),
    }),
    removeUser: builder.mutation({
      query: (id) => ({ url: `/api/users/${id}`, method: 'DELETE' }),
    }),
    health: builder.query({
      query: () => '/health',
    }),
  }),
});
