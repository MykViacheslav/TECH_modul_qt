import { redirect } from 'next/navigation';

export default function ModulesRedirectPage() {
  redirect('/workspace?mode=modules');
}
