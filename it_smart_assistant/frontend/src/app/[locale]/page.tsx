import Link from "next/link";
import { Button, Card, CardHeader, CardTitle, CardContent } from "@/components/ui";
import { APP_DESCRIPTION, APP_NAME, ROUTES } from "@/lib/constants";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto py-16 px-4">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-4">
            {APP_NAME}
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            {APP_DESCRIPTION}
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 max-w-5xl mx-auto">
          
          <Card>
            <CardHeader>
              <CardTitle>Xác thực</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="mb-4 text-muted-foreground">
                Đăng nhập an toàn để sử dụng chatbot và quản lý hội thoại
              </p>
              <div className="flex gap-2">
                <Button asChild>
                  <Link href={ROUTES.LOGIN}>Đăng nhập</Link>
                </Button>
                <Button variant="outline" asChild>
                  <Link href={ROUTES.REGISTER}>Đăng ký</Link>
                </Button>
              </div>
            </CardContent>
          </Card>
          

          
          <Card>
            <CardHeader>
              <CardTitle>Chatbot sinh viên</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="mb-4 text-muted-foreground">
                Tra cứu thông tin học vụ và nhận hỗ trợ từ {APP_NAME}
              </p>
              <Button asChild>
                <Link href={ROUTES.CHAT}>Bắt đầu trò chuyện</Link>
              </Button>
            </CardContent>
          </Card>
          

          <Card>
            <CardHeader>
              <CardTitle>Tổng quan</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="mb-4 text-muted-foreground">
                Xem trạng thái hệ thống và quản lý tài khoản của bạn
              </p>
              <Button variant="outline" asChild>
                <Link href={ROUTES.DASHBOARD}>Mở tổng quan</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
