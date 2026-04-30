import { redirect } from "next/navigation";

export default function WallPageRedirect() {
  redirect("/workspace?mode=connections");
}
