
import { createClient, SupabaseClient } from '@supabase/supabase-js';

/**
 * Inicializa e exporta o cliente Supabase para uso global no projeto.
 * A chave de API deve ser definida via variável de ambiente.
 * Nunca exponha chaves sensíveis no código-fonte.
 */

const supabaseUrl: string = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://bnfdhszfrsxzdgfzjxvy.supabase.co';
const supabaseKey: string | undefined = process.env.NEXT_PUBLIC_SUPABASE_KEY;

if (!supabaseKey) {
	throw new Error('Supabase API key não definida. Configure NEXT_PUBLIC_SUPABASE_KEY no .env.local');
}

export const supabase: SupabaseClient = createClient(supabaseUrl, supabaseKey);