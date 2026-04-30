import { redirect } from 'next/navigation';

export default function KompletRedirectPage() {
  redirect('/workspace?mode=komplet');
}
