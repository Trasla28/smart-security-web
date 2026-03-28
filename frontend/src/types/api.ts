export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pages: number;
  size: number;
}

export interface ApiError {
  detail: string;
  code?: string;
}
