output "vscode" {
  value = "http://${aws_instance.gpu_box.public_ip}:8080"
}
