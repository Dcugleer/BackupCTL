import { createClient } from '@supabase/supabase-js';

const supabaseUrl = 'https://bnfdhszfrsxzdgfzjxvy.supabase.co';
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJuZmRoc3pmcnN4emRnZnpqeHZ5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI1NDY0MTIsImV4cCI6MjA3ODEyMjQxMn0.ctGYMHh_wt46ymuZaJ8GG6rwFZUoNezXef4P8gsOvRg';
export const supabase = createClient(supabaseUrl, supabaseKey);